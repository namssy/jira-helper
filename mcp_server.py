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
    instructions="Jira Cloud 티켓 조회·검색 (내 이슈 목록, 상세, JQL 검색)",
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


def main() -> None:
    # Cursor는 기본적으로 stdio로 MCP 서버를 실행함
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
