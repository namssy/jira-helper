# Jira 티켓 생성 시 필수 커스텀 필드 (MCP / CLI)

일부 프로젝트(예: CLOSET)는 Bug 등 이슈 타입 생성 시 **필수 커스텀 필드**가 있어, 값을 넣지 않으면 API 생성이 실패합니다.

jira-helper는 `config/required_fields.json`에 정의된 기본값을 자동으로 넣어 주므로, **CLI**나 **MCP `jira_create`**로 Bug 티켓을 만들 때 별도로 필드를 지정하지 않아도 생성됩니다.  
필요하면 `custom_fields`(CLI: `--custom-fields`, MCP: `custom_fields_json`)로 **덮어쓰기**할 수 있습니다.

---

## CLOSET 프로젝트 – Bug

| 필드명 | customfield ID | 기본값 (config) | 타입 | 선택지(옵션 ID) |
|--------|----------------|------------------|------|------------------|
| Issue Category | customfield_10414 | Functional (11729) | multicheckboxes | Data(11735), Functional(11729), Regression(11736), Security(11732), User Interface(11731) |
| Live/Staging/Both | customfield_10648 | Both (12603) | radiobuttons | Live(12601), Staging(12602), Both(12603) |
| 기능 영향 범위(Feature Impact Scope) | customfield_11947 | Search (14834) | multicheckboxes | Upload(14830), Versioning(14831), Library/Asset(14832), Linesheet(14833), **Search(14834)**, Viewer/3D(14835), Permissions(14836), Integration(14837), DB Write(14838), Rendering(14839), Caching(14840), WebSocket(14841), Workflow(14842), External Link(14843), Developer Tools(14844) |
| 작업 내용/재현 방법(Work Detail/Reproduction Sequence) | customfield_11913 | `__from_description__` | textarea | 설명(description) 본문이 그대로 들어감. 비면 플레이스홀더 문구 사용 |
| 기대 결과(Expected Output) | customfield_11914 | `__from_description__` | textarea | 동일 |

- **`__from_description__`**: 생성 시 전달한 `description` 문자열이 들어갑니다. 비어 있으면 `"재현 방법/기대 결과를 설명에 기입해주세요."`가 들어갑니다.

---

## MCP에서 사용 예

- **기본값으로 생성** (설명만 넣으면 됨):
  - `jira_create(project_key="CLOSET", summary="버그 요약", issuetype="Bug", description="재현 단계:\n1. ...\n기대 결과: ...")`
- **Live/Staging/Both만 Live로 바꿔서 생성**:
  - `custom_fields_json='{"customfield_10648":{"id":"12601"}}'` 로 호출

---

## CLI에서 사용 예

```bash
# 기본값으로 CLOSET Bug 생성 (config 기본값 적용)
jira create CLOSET "버그 제목" --type Bug -d "재현 방법 및 기대 결과"

# Live로 지정해서 생성
jira create CLOSET "버그 제목" --type Bug -d "설명" --custom-fields '{"customfield_10648":{"id":"12601"}}'
```

---

## 설정 파일 위치

- `config/required_fields.json` (프로젝트 루트 또는 패키지 내 config)
- 환경변수 `JIRA_REQUIRED_FIELDS` 로 다른 JSON 파일 경로 지정 가능

파일 구조 예:

```json
{
  "CLOSET": {
    "Bug": {
      "customfield_10414": [{"id": "11729"}],
      "customfield_10648": {"id": "12603"},
      "customfield_11947": [{"id": "14834"}],
      "customfield_11913": "__from_description__",
      "customfield_11914": "__from_description__"
    }
  }
}
```

다른 프로젝트/이슈 타입을 추가할 때는 Jira **Create metadata** API로 해당 프로젝트·이슈타입의 필수 필드 ID와 허용 값을 확인한 뒤, 위와 같은 형태로 추가하면 됩니다.
