#!/usr/bin/env python3
"""
Jira MCP Server - Cursor 등에서 "지라 티켓 조회해줘"처럼 도구로 호출 가능.
설정: JIRA_ENV, .env(cwd), ~/.config/jira-helper/.env (jira_cli와 동일)
"""
from __future__ import annotations

import sys
from pathlib import Path

# 프로젝트 루트에서 jira_cli 로드 (pip install -e . 한 경우에도 동작)
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("mcp 패키지가 필요합니다: pip install mcp", file=sys.stderr)
    sys.exit(1)

import jira_cli

mcp = FastMCP(
    "jira-helper",
    instructions="Jira Cloud 티켓 조회·검색·생성·수정 (내 이슈 목록, 상세, JQL 검색, 티켓 생성/수정)",
)


@mcp.tool()
def jira_list(
    status: str = "open",
    max_results: int = 20,
) -> str:
    """내게 할당된 Jira 티켓 목록을 조회합니다.
    - status: open(미완료), done(완료), all(전체). 기본값 open.
    - max_results: 최대 개수. 기본값 20.
    """
    try:
        issues = jira_cli.my_issues(status=status, max_results=max_results)
        label = {"open": "미완료", "done": "완료", "all": "전체"}.get(status, status)
        return f"내 티켓 ({label}, {len(issues)}건)\n" + jira_cli.format_issue_list(issues)
    except Exception as e:
        return f"오류: {e}"


@mcp.tool()
def jira_show(issue_key: str) -> str:
    """Jira 티켓 한 건의 상세 정보를 조회합니다.
    - issue_key: 이슈 키 (예: PROJ-123)
    """
    try:
        data = jira_cli.get_issue(issue_key)
        return jira_cli.format_issue_detail(data)
    except Exception as e:
        return f"오류: {e}"


@mcp.tool()
def jira_search(jql: str, max_results: int = 20) -> str:
    """JQL로 Jira 이슈를 검색합니다.
    - jql: Jira Query Language (예: project = MYPROJ AND status = 'In Progress')
    - max_results: 최대 개수. 기본값 20.
    """
    try:
        issues = jira_cli.search(jql, max_results=max_results)
        return f"검색 결과 ({len(issues)}건)\n" + jira_cli.format_issue_list(issues)
    except Exception as e:
        return f"오류: {e}"


@mcp.tool()
def jira_transition(issue_key: str, target_status: str) -> str:
    """Jira 티켓의 상태를 변경합니다.
    - issue_key: 이슈 키 (예: PROJ-123)
    - target_status: 목표 상태명. 예: In Progress(착수), Resolved(해결), Closed(완료).
      부분 일치 지원 (예: 'progress'로 In Progress 전환 가능).
    """
    try:
        ok, msg = jira_cli.transition_to_status(issue_key, target_status)
        return msg
    except Exception as e:
        return f"오류: {e}"


@mcp.tool()
def jira_create(
    project_key: str,
    summary: str,
    issuetype: str = "Task",
    description: str = "",
    assign_to_self: bool = False,
    custom_fields_json: str = "",
) -> str:
    """Jira 티켓을 생성합니다.
    - project_key: 프로젝트 키 (예: PROJ, CLOSET)
    - summary: 티켓 제목
    - issuetype: 이슈 타입 (예: Task, Bug, Story). 기본값 Task.
    - description: 설명(플레인 텍스트). Bug 시 필수 커스텀 필드(재현 방법/기대 결과)에 사용됨.
    - assign_to_self: True면 현재 사용자를 담당자로 지정.
    - custom_fields_json: 커스텀 필드 덮어쓰기(JSON 문자열). 비우면 config/required_fields.json 기본값 사용.
      CLOSET Bug 필수 필드: Issue Category, Live/Staging/Both, 기대 결과, 작업 내용/재현 방법, 기능 영향 범위.
      자세한 옵션은 docs/MCP_REQUIRED_FIELDS.md 참고.
    """
    try:
        custom_fields = None
        if custom_fields_json and custom_fields_json.strip():
            import json
            custom_fields = json.loads(custom_fields_json.strip())
        key, url = jira_cli.create_issue(
            project_key=project_key,
            summary=summary,
            issuetype=issuetype,
            description=description or None,
            assign_to_self=assign_to_self,
            custom_fields=custom_fields,
        )
        return f"생성됨: {key}\n{url}"
    except Exception as e:
        return f"오류: {e}"


@mcp.tool()
def jira_edit(
    issue_key: str,
    summary: str = "",
    description: str = "",
    assign_to_self: bool = False,
) -> str:
    """Jira 티켓을 수정합니다. 지정한 필드만 변경됩니다.
    - issue_key: 이슈 키 (예: PROJ-123)
    - summary: 새 제목. 비우면 변경 안 함.
    - description: 새 설명(플레인 텍스트). 비우면 변경 안 함.
    - assign_to_self: True면 현재 사용자를 담당자로 지정.
    """
    try:
        ok, msg = jira_cli.update_issue(
            issue_key=issue_key,
            summary=summary or None,
            description=description or None,
            assign_to_self=assign_to_self,
        )
        return msg
    except Exception as e:
        return f"오류: {e}"


def main() -> None:
    # Cursor는 기본적으로 stdio로 MCP 서버를 실행함
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
