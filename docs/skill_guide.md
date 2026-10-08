# sootool.skill_guide

에이전트가 "이 요청에 어떤 도구를 불러야 하는가"를 판단하도록 돕는 안내 도구다. 트리거 표, 호출 예시, 금지 패턴, 여러 단계 계산 절차(플레이북)를 JSON으로 돌려준다. 세션을 시작할 때 한 번 호출하게 하면 에이전트가 숫자를 직접 계산하지 않고 도구를 부르는 비율이 높아진다.

## 호출

```
sootool.skill_guide(section="all", lang=None)
```

|인자|기본값|값|
|-|-|-|
|`section`|`all`|`triggers`, `examples`, `anti_patterns`, `playbooks`, `all`|
|`lang`|자동|`ko`, `en`. 지원하지 않는 값은 `ko`로 처리한다.|

`lang`을 주지 않으면 HTTP 요청의 `Accept-Language`, 환경변수 `SOOTOOL_LOCALE`, 기본값 `ko` 순으로 정한다.

CLI: `sootool skill-guide --section playbooks --lang en`

## 반환 구조

```json
{
  "version":       "1.0.0",
  "locale":        "ko",
  "triggers":      [ ... ],
  "examples":      [ ... ],
  "anti_patterns": [ ... ],
  "playbooks":     [ ... ]
}
```

`section`을 지정하면 해당 키만 담긴다.

|섹션|항목 형식|예|
|-|-|-|
|`triggers`|`signal`, `tool`, `reason`|"숫자 두 개 이상 사칙연산" → `core.add / core.sub / core.mul / core.div 또는 core.batch`|
|`examples`|`request`, `tool_call`, `expected_output`|"500만원에서 부가세 분리해줘" → `accounting.vat_extract(gross="5000000", rate="0.1")` → `net "4545454"`, `vat "454546"`|
|`anti_patterns`|`pattern`, `why`, `instead`|프롬프트에 `3 + 5 = 8`을 직접 쓰고 검증 생략 → `core.add`를 부르고 trace를 인용|
|`playbooks`|`id`, `scenario`, `steps`|`payroll_to_net`: 월급 → 연봉 → 소득세 → 실수령액을 `core.pipeline` 단계로|

## 플레이북 목록

|id|내용|
|-|-|
|`payroll_to_net`|월급 → 연봉 → 소득세 → 실수령액|
|`payroll_full_net`|월급과 식대에서 4대보험·소득세를 뺀 실수령액|
|`vat_batch_summary`|거래 여러 건의 부가세 분리 후 합계|
|`loan_compare_3`|대출 조건 3안 비교|
|`npv_sensitivity`|할인율별 NPV 민감도|
|`bond_yield_duration`|채권 수익률과 듀레이션|
|`ab_test_full`|A/B 검정: t-검정, 신뢰구간, 효과크기|
|`math_integration_npv`|연속 현금흐름을 수치 적분해 NPV 검증|
|`lunar_holiday_planner`|음력 명절의 양력 날짜와 주변 영업일|
|`medical_dose_with_qtc`|체중 기반 투약량과 QT 보정(약물 안전 확인)|
|`engineering_electrical_audit`|전압·전류·저항·전력을 옴의 법칙, 전력 식, 병렬 저항으로 교차 확인|
|`policy_annual_update`|정책 연간 갱신(propose → activate)|
|`policy_hotfix_rollback`|잘못 반영한 정책 되돌리기|
|`policy_portability`|정책 번들 내보내기와 가져오기|

플레이북의 `<월급>`, `<연도>` 같은 자리 표시는 실제 값으로 바꿔 쓴다.

## 버전

`version`은 SemVer를 따른다. 설명이나 예시 보완은 PATCH, 트리거·플레이북 추가는 MINOR, 기존 필드의 의미나 반환 구조가 바뀌면 MAJOR를 올린다.

## 함께 쓰는 장치

- 서버는 MCP `instructions` 필드에 "수치 계산은 도구로" 지시를 싣는다.
- 모든 응답의 `_meta.hints`가 호출 패턴을 보고 다음 도구를 제안한다(같은 산술 반복, 세무 계산의 trace 생략, 지난 연도 정책 사용 등).
- 클라이언트 설정에 붙여 넣을 규칙 스니펫: [Claude Code](integration/claude-md-snippet.md), [Cursor](integration/cursor-rules-snippet.md), [AGENTS.md](integration/agents-md-snippet.md)
