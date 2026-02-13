#!/usr/bin/env python3
"""
Jira 티켓 관리 CLI - 내 이슈 조회, 검색, 상세 보기, 티켓 생성·수정
"""
import os
import sys
import argparse
from urllib.parse import quote

import requests
from dotenv import load_dotenv


def _load_config():
    """설정 로드 순서: JIRA_ENV 경로 → 현재 디렉터리 .env → ~/.config/jira-helper/.env"""
    env_path = os.getenv("JIRA_ENV")
    if env_path and os.path.isfile(env_path):
        load_dotenv(env_path)
        return
    if load_dotenv(".env"):
        return
    default = os.path.expanduser("~/.config/jira-helper/.env")
    if os.path.isfile(default):
        load_dotenv(default)


_load_config()

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")


def get_auth():
    if not all([JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN]):
        print("오류: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN을 설정해주세요.")
        print("  - 현재 디렉터리: .env")
        print("  - 전역 설정: ~/.config/jira-helper/.env")
        print("  - 또는 환경변수 JIRA_ENV=/path/to/.env 로 파일 지정")
        sys.exit(1)
    return (JIRA_EMAIL, JIRA_API_TOKEN)


def api_get(path, params=None):
    url = f"{JIRA_BASE_URL}/rest/api/3{path}"
    r = requests.get(url, auth=get_auth(), params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def api_post(path, json_data=None):
    url = f"{JIRA_BASE_URL}/rest/api/3{path}"
    r = requests.post(url, auth=get_auth(), json=json_data, timeout=30)
    r.raise_for_status()
    if r.status_code == 204 or not r.text.strip():
        return {}
    return r.json()


def api_put(path, json_data=None):
    url = f"{JIRA_BASE_URL}/rest/api/3{path}"
    r = requests.put(url, auth=get_auth(), json=json_data, timeout=30)
    r.raise_for_status()
    if r.status_code == 204 or not r.text.strip():
        return {}
    return r.json()


def my_issues(status=None, max_results=20):
    """내게 할당된 이슈 목록 (기본: 미완료)"""
    jql = "assignee = currentUser()"
    if status and status.lower() != "all":
        if status.lower() == "done":
            jql += " AND status = Done"
        else:
            jql += " AND status != Done"
    else:
        jql += " AND status != Done"
    jql += " ORDER BY updated DESC"
    data = api_post("/search/jql", json_data={
        "jql": jql,
        "maxResults": max_results,
        "fields": ["summary", "status", "priority", "updated", "issuetype"],
    })
    return data.get("issues", [])


def show_issue(issue_key):
    """티켓 한 건 상세 조회"""
    data = get_issue(issue_key)
    print("\n" + format_issue_detail(data) + "\n")
    return data


def get_transitions(issue_key):
    """이슈에 적용 가능한 전환(transition) 목록 조회"""
    data = api_get(f"/issue/{issue_key}/transitions")
    return data.get("transitions", [])


def transition_issue(issue_key, transition_id):
    """이슈 상태 전환 실행"""
    api_post(f"/issue/{issue_key}/transitions", json_data={"transition": {"id": transition_id}})


def start_issue(issue_key):
    """티켓을 착수(In Progress) 상태로 전환. In Progress로 가는 전환만 적용."""
    transitions = get_transitions(issue_key)
    for t in transitions:
        to_status = (t.get("to") or {}).get("name", "")
        if to_status and "progress" in to_status.lower():
            transition_issue(issue_key, t["id"])
            return to_status
    return None


def transition_to_status(issue_key, target_status):
    """티켓을 지정한 상태로 전환.
    target_status: 목표 상태명 (예: In Progress, Resolved, Closed). 부분 일치 지원.
    반환: (성공여부, 메시지)
    """
    transitions = get_transitions(issue_key)
    target_lower = (target_status or "").strip().lower()
    if not target_lower:
        available = [((t.get("to") or {}).get("name", "?"), t.get("name", "")) for t in transitions]
        return False, f"target_status를 지정해주세요. 가능한 전환: {available}"
    for t in transitions:
        to_status = (t.get("to") or {}).get("name", "")
        if to_status and (target_lower in to_status.lower() or to_status.lower() == target_lower):
            transition_issue(issue_key, t["id"])
            return True, f"{issue_key} → {to_status} 로 변경되었습니다."
    available = [((t.get("to") or {}).get("name", "?"), t.get("name", "")) for t in transitions]
    return False, f"'{target_status}'로 전환할 수 없습니다. 가능한 전환: {available}"


def search(jql, max_results=20):
    """JQL로 검색"""
    data = api_post("/search/jql", json_data={
        "jql": jql,
        "maxResults": max_results,
        "fields": ["summary", "status", "priority", "updated", "issuetype"],
    })
    return data.get("issues", [])


def _description_to_adf(plain_text):
    """플레인 텍스트를 Jira Cloud ADF(Atlassian Document Format)로 변환."""
    if not (plain_text or plain_text.strip()):
        return None
    text = plain_text.strip()
    # 한 줄이면 paragraph 하나, 여러 줄이면 줄마다 paragraph
    blocks = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        blocks.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": line}],
        })
    if not blocks:
        return None
    return {"type": "doc", "version": 1, "content": blocks}


def create_issue(
    project_key,
    summary,
    issuetype="Task",
    description=None,
    assign_to_self=False,
    custom_fields=None,
):
    """티켓을 생성하고 생성된 이슈 키를 반환.
    project_key: 프로젝트 키 (예: PROJ)
    summary: 제목
    issuetype: 이슈 타입 이름 (예: Task, Bug, Story). 기본 Task.
    description: 본문 플레인 텍스트 (선택)
    assign_to_self: True면 현재 사용자에게 담당자 지정
    custom_fields: 프로젝트별 필수 커스텀 필드 { "customfield_12345": value } (선택)
    반환: (issue_key, browse_url) 또는 실패 시 예외.
    """
    fields = {
        "project": {"key": project_key.strip().upper()},
        "summary": summary.strip(),
        "issuetype": {"name": issuetype.strip()},
    }
    if description:
        adf = _description_to_adf(description)
        if adf:
            fields["description"] = adf
    if assign_to_self:
        me = api_get("/myself")
        fields["assignee"] = {"accountId": me.get("accountId")}
    if custom_fields:
        fields.update(custom_fields)
    data = api_post("/issue", json_data={"fields": fields})
    key = data.get("key")
    url = f"{JIRA_BASE_URL}/browse/{key}" if key else ""
    return key, url


def update_issue(issue_key, summary=None, description=None, assign_to_self=False):
    """티켓 필드를 수정합니다. 지정한 필드만 변경됩니다.
    summary: 제목 (None이면 변경 안 함)
    description: 본문 플레인 텍스트 (None이면 변경 안 함)
    assign_to_self: True면 담당자를 현재 사용자로 설정
    """
    fields = {}
    if summary is not None:
        fields["summary"] = summary.strip()
    if description is not None:
        adf = _description_to_adf(description)
        if adf:
            fields["description"] = adf
    if assign_to_self:
        me = api_get("/myself")
        fields["assignee"] = {"accountId": me.get("accountId")}
    if not fields:
        return False, "변경할 필드를 지정해주세요. (--summary, --description, --assign-me 중 하나 이상)"
    api_put(f"/issue/{issue_key}", json_data={"fields": fields})
    return True, f"{issue_key} 수정되었습니다."


def print_issue_list(issues):
    if not issues:
        print("결과 없음.")
        return
    print(format_issue_list(issues))


def format_issue_list(issues):
    """이슈 목록을 문자열로 포맷 (MCP 등에서 재사용)."""
    if not issues:
        return "결과 없음."
    lines = []
    for i in issues:
        key = i["key"]
        f = i.get("fields", {})
        summary = (f.get("summary") or "")[:50]
        status = (f.get("status") or {}).get("name", "?")
        typ = (f.get("issuetype") or {}).get("name", "?")
        lines.append(f"  {key:12} {status:12} {typ:10} {summary}")
    return "\n".join(lines)


def get_issue(issue_key):
    """티켓 한 건 raw 데이터 조회 (출력 없음, MCP 등에서 재사용)."""
    return api_get(f"/issue/{issue_key}")


def format_issue_detail(data):
    """이슈 상세를 문자열로 포맷 (MCP 등에서 재사용)."""
    fields = data.get("fields", {})
    status = fields.get("status", {}).get("name", "?")
    summary = fields.get("summary", "")
    issue_type = fields.get("issuetype", {}).get("name", "?")
    priority = fields.get("priority", {}).get("name", "—")
    assignee = (fields.get("assignee") or {}).get("displayName", "—")
    updated = fields.get("updated", "")[:10]
    raw_desc = fields.get("description")
    desc_text = ""
    if isinstance(raw_desc, str):
        desc_text = raw_desc
    elif isinstance(raw_desc, dict):
        desc = raw_desc.get("content", [])
        for block in desc:
            if block.get("type") == "paragraph":
                for c in block.get("content", []):
                    if c.get("type") == "text":
                        desc_text += c.get("text", "")
                desc_text += "\n"
    lines = [
        f"[{data['key']}] {summary}",
        f"  타입: {issue_type}  |  상태: {status}  |  우선순위: {priority}",
        f"  담당: {assignee}  |  수정: {updated}",
        f"  URL: {JIRA_BASE_URL}/browse/{data['key']}",
    ]
    if desc_text.strip():
        lines.append("\n--- 설명 ---")
        lines.append(desc_text.strip())
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Jira 티켓 관리 CLI")
    sub = parser.add_subparsers(dest="cmd", help="명령")

    # 내 이슈 목록
    p_list = sub.add_parser("list", help="내게 할당된 티켓 목록 (미완료)")
    p_list.add_argument("--status", choices=["open", "done", "all"], default="open", help="open=미완료, done=완료, all=전체")
    p_list.add_argument("-n", "--max", type=int, default=20, help="최대 개수")

    # 티켓 상세
    p_show = sub.add_parser("show", help="티켓 상세 보기 (예: show PROJ-123)")
    p_show.add_argument("issue_key", help="이슈 키 (예: PROJ-123)")

    # JQL 검색
    p_search = sub.add_parser("search", help="JQL로 검색")
    p_search.add_argument("jql", help='JQL (예: "project = MYPROJ AND status = In Progress")')
    p_search.add_argument("-n", "--max", type=int, default=20)

    # 티켓 착수 (In Progress)
    p_start = sub.add_parser("start", help="티켓을 착수(In Progress) 상태로 전환")
    p_start.add_argument("issue_key", help="이슈 키 (예: PROJ-123)")

    # 티켓 상태 전환
    p_transition = sub.add_parser("transition", help="티켓 상태 변경 (예: transition PROJ-123 Resolved)")
    p_transition.add_argument("issue_key", help="이슈 키 (예: PROJ-123)")
    p_transition.add_argument("target_status", help="목표 상태 (예: In Progress, Resolved, Closed)")

    # 티켓 생성
    p_create = sub.add_parser("create", help="티켓 생성 (예: create PROJ '제목' [옵션])")
    p_create.add_argument("project", help="프로젝트 키 (예: PROJ)")
    p_create.add_argument("summary", help="티켓 제목")
    p_create.add_argument("--type", dest="issuetype", default="Task", help="이슈 타입 (기본: Task)")
    p_create.add_argument("--description", "-d", help="설명 (플레인 텍스트)")
    p_create.add_argument("--assign-me", action="store_true", help="나에게 담당자 지정")

    # 티켓 수정
    p_edit = sub.add_parser("edit", help="티켓 수정 (제목·설명·담당자)")
    p_edit.add_argument("issue_key", help="이슈 키 (예: PROJ-123)")
    p_edit.add_argument("--summary", "-s", help="새 제목")
    p_edit.add_argument("--description", "-d", help="새 설명 (플레인 텍스트)")
    p_edit.add_argument("--assign-me", action="store_true", help="나에게 담당자 지정")

    args = parser.parse_args()

    if args.cmd == "list":
        issues = my_issues(status=args.status, max_results=args.max)
        print(f"\n내 티켓 ({len(issues)}건)")
        print_issue_list(issues)
        print()

    elif args.cmd == "show":
        show_issue(args.issue_key)

    elif args.cmd == "search":
        issues = search(args.jql, max_results=args.max)
        print(f"\n검색 결과 ({len(issues)}건)")
        print_issue_list(issues)
        print()

    elif args.cmd == "start":
        new_status = start_issue(args.issue_key)
        if new_status:
            print(f"\n{args.issue_key} → {new_status} 로 변경되었습니다.")
        else:
            print(f"\n오류: {args.issue_key}에서 'In Progress'로 전환할 수 있는 전환이 없습니다.")
            print("  가능한 전환: ", end="")
            for t in get_transitions(args.issue_key):
                to_name = (t.get("to") or {}).get("name", "?")
                print(f" {t['name']}→{to_name}", end="")
            print()

    elif args.cmd == "transition":
        ok, msg = transition_to_status(args.issue_key, args.target_status)
        print(f"\n{msg}")

    elif args.cmd == "create":
        key, url = create_issue(
            project_key=args.project,
            summary=args.summary,
            issuetype=args.issuetype,
            description=args.description,
            assign_to_self=args.assign_me,
        )
        print(f"\n생성됨: {key}")
        print(f"  {url}")

    elif args.cmd == "edit":
        ok, msg = update_issue(
            issue_key=args.issue_key,
            summary=args.summary,
            description=args.description,
            assign_to_self=args.assign_me,
        )
        print(f"\n{msg}")

    else:
        parser.print_help()
        print("\n예시:")
        print("  python jira_cli.py list              # 내 미완료 티켓")
        print("  python jira_cli.py list --status done # 내 완료 티켓")
        print("  python jira_cli.py show PROJ-123      # 티켓 상세")
        print('  python jira_cli.py search "project = MYPROJ"  # JQL 검색')
        print("  python jira_cli.py create PROJ '제목' --assign-me  # 티켓 생성")
        print("  python jira_cli.py edit PROJ-123 -s '새 제목' -d '새 설명'  # 티켓 수정")


if __name__ == "__main__":
    main()
