# Jira 티켓 관리 CLI

Jira Cloud REST API로 내 티켓을 조회·검색·상태 전환하는 간단한 CLI 도구입니다.

## 설정

1. **가상환경 만들기 및 의존성 설치** (권장)

   macOS 등에서 시스템 Python이 PEP 668(externally-managed-environment)인 경우, 가상환경을 쓰는 것이 안전합니다.

   ```bash
   cd ~/jira-helper
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   가상환경을 쓰지 않는다면:

   ```bash
   pip install -r requirements.txt
   # 또는
   pip install requests python-dotenv
   ```

2. **환경 변수**
   - `.env.example`을 복사해 `.env` 생성 (프로젝트 내 사용) 또는 `~/.config/jira-helper/.env` (전역 사용)
   - Jira Cloud URL, 이메일, API 토큰 입력

   ```bash
   cp .env.example .env
   # .env 편집: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
   ```

   **API 토큰 발급:** [Atlassian API 토큰](https://id.atlassian.com/manage-profile/security/api-tokens)에서 생성 (비밀번호 대신 사용)

## 사용법

가상환경을 켠 뒤 실행:

```bash
cd ~/jira-helper
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python jira_cli.py list
```

가상환경 없이 한 번에 실행하려면 프로젝트의 Python을 직접 지정:

```bash
~/jira-helper/.venv/bin/python ~/jira-helper/jira_cli.py list
```

**명령 예시**

```bash
# 내 미완료 티켓 목록 (기본)
python jira_cli.py list

# 내 완료 티켓만
python jira_cli.py list --status done

# 전체(미완료+완료)
python jira_cli.py list --status all

# 티켓 상세 보기
python jira_cli.py show PROJ-123

# JQL로 검색
python jira_cli.py search "project = MYPROJ AND status = 'In Progress'"
python jira_cli.py search "assignee = currentUser() ORDER BY updated DESC" -n 10

# 티켓 착수 (In Progress로 전환)
python jira_cli.py start PROJ-123

# 티켓 상태 변경 (Resolved, Closed 등)
python jira_cli.py transition PROJ-123 Resolved
```

## 쉘 별칭 (선택)

`~/.zshrc`에 추가하면 `jira list`처럼 쓸 수 있습니다. 가상환경의 Python을 쓰려면:

```bash
alias jira='~/jira-helper/.venv/bin/python ~/jira-helper/jira_cli.py'
```

가상환경 없이 시스템 Python을 쓰는 경우:

```bash
alias jira='python ~/jira-helper/jira_cli.py'
```

## 다른 프로젝트에서 사용하기

어느 디렉터리에서나 `jira` 명령을 쓰려면 **전역 설치**와 **전역 설정**을 쓰면 됩니다.

### 1. 전역 설치

**pipx** (권장: 전용 가상환경으로 설치되어 다른 패키지와 격리됨):

```bash
pipx install ~/jira-helper
# 또는 GitHub 클론 후
git clone https://github.com/your-id/jira-helper.git && pipx install ./jira-helper
# 개발 중 변경 반영하려면: pipx install -e ~/jira-helper
```

**pip** (기존 가상환경에 설치):

```bash
cd ~/jira-helper
pip install -e .
```

설치 후 `jira` 명령이 PATH에 등록됩니다.

### 2. 설정 로드 순서

CLI는 아래 순서로 설정 파일을 찾습니다.

1. **JIRA_ENV** 환경 변수에 지정한 파일 경로
2. **현재 디렉터리**의 `.env`
3. **~/.config/jira-helper/.env** (전역 기본값)

다른 프로젝트에서도 같은 Jira를 쓸 때는 전역 설정 하나만 두면 됩니다.

```bash
mkdir -p ~/.config/jira-helper
cp ~/jira-helper/.env.example ~/.config/jira-helper/.env
# ~/.config/jira-helper/.env 편집
```

특정 프로젝트만 다른 Jira(다른 URL/계정)를 쓰려면 그 프로젝트 디렉터리에 `.env`를 두면, 그 디렉터리에서 실행할 때만 그 설정이 사용됩니다.

### 3. 사용 예

```bash
cd ~/any-project
jira list
jira show PROJ-123
```

## MCP 서버로 사용하기 (Cursor 등)

MCP(Model Context Protocol) 서버로 등록하면 Cursor에서 **"지라 티켓 목록 조회해줘"**, **"PROJ-123 티켓 보여줘"**처럼 자연어로 요청할 수 있습니다.

### 전역 MCP (모든 Cursor 프로젝트에서 사용)

1. **pipx로 전역 설치** (한 번만):

   ```bash
   pipx install -e ~/jira-helper
   ```

   `jira`, `jira-mcp` 명령이 PATH에 등록됩니다.

2. **전역 설정 파일** (`~/.config/jira-helper/.env`):

   ```bash
   mkdir -p ~/.config/jira-helper
   cp ~/jira-helper/.env.example ~/.config/jira-helper/.env
   # ~/.config/jira-helper/.env 에 JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN 입력
   ```

   MCP 서버는 현재 디렉터리 `.env`가 없으면 이 파일을 사용합니다.

3. **Cursor 전역 MCP 설정** (`~/.cursor/mcp.json`):

   `mcpServers`에 다음을 추가합니다.

   ```json
   "jira-helper": {
     "command": "jira-mcp"
   }
   ```

   Cursor를 재시작하면 모든 워크스페이스에서 jira-helper MCP를 쓸 수 있습니다.

### 프로젝트별 MCP (이 프로젝트에서만)

이 프로젝트에서만 MCP를 쓰려면 프로젝트 가상환경의 Python으로 `mcp_server.py`를 직접 실행합니다. (전역 설치 없음)

1. **의존성 설치**

   ```bash
   cd ~/jira-helper
   pip install -e .
   # (mcp는 기본 의존성에 포함됨)
   ```

2. **Cursor에 MCP 서버 등록** (프로젝트 `.cursor/mcp.json`)

   ```json
   {
     "mcpServers": {
       "jira-helper": {
         "command": "~/jira-helper/.venv/bin/python",
         "args": ["~/jira-helper/mcp_server.py"]
       }
     }
   }
   ```

   다른 경로에 클론했다면 해당 경로로 바꾸세요.

### 제공 도구

| 도구 | 설명 |
|------|------|
| **jira_list** | 내게 할당된 티켓 목록 (status: open/done/all, max_results) |
| **jira_show** | 티켓 한 건 상세 (issue_key) |
| **jira_search** | JQL 검색 (jql, max_results) |
| **jira_transition** | 티켓 상태 변경 (issue_key, target_status: In Progress/Resolved/Closed 등) |

설정은 CLI와 동일하게 **JIRA_ENV**, **.env**(현재 디렉터리), **~/.config/jira-helper/.env** 순으로 로드됩니다.

## Cursor에서 티켓 참조하기

코드 작업 시 "PROJ-123 티켓 기준으로 수정해줘"처럼 말하면, 이 CLI로 `show PROJ-123` 결과를 참고해 작업할 수 있습니다.  
MCP 서버를 켜 두면 Cursor가 직접 `jira_show` 등을 호출해 티켓 내용을 가져올 수 있습니다.  
원하면 `.cursor/rules`에 Jira 티켓 번호를 커밋/브랜치에 포함하는 규칙도 추가할 수 있습니다.
