# 정책 파일 관리

세율, 공제액, 보험료율 같은 법정 값은 코드가 아니라 정책 파일(YAML)에 있다. 이 문서는 정책 파일의 구조, 계산 시 버전이 선택되는 규칙, 서버를 다시 배포하지 않고 정책을 갱신하는 절차를 다룬다.

## 두 저장소

```
패키지 저장소 (읽기 전용, 패키지에 포함)
  src/sootool/policies/<도메인>/<이름>_<연도>.yaml

덮어쓰기 저장소 (사용자가 쓰기 가능, 아래 순서로 결정)
  $SOOTOOL_POLICY_DIR/<도메인>/...
  $XDG_DATA_HOME/sootool/policies/<도메인>/...
  ~/.local/share/sootool/policies/<도메인>/...
```

로더는 덮어쓰기 저장소를 먼저 보고, 없으면 패키지 저장소를 쓴다. 어느 쪽을 썼는지는 응답의 `policy_source`(`package` 또는 `override`)로 알 수 있다. 덮어쓰기 정책으로 계산한 응답에는 `_meta.hints`에 `override_policy_in_use` 신호가 붙는다. 서버가 시작할 때 사용 중인 덮어쓰기 경로를 INFO 로그로 남긴다.

## 정책 파일 구조

```yaml
sha256: "<자체 해시>"
effective_date: "2027-01-01"      # 시행 시작일(포함)
effective_to:   "2027-06-30"      # 선택. 시행 종료일(포함). 없으면 계속 시행
status: enacted                   # enacted(기본) | proposed(개정안) | superseded(교체됨)
version: "2027.1"                 # 선택. 표시용 이름
notice_no: "소득세법 제55조제1항 ..."   # 사람이 읽는 근거 표기
source_url: "https://www.law.go.kr/..."
citations:                        # 구조화된 근거 조문. 개정안(proposed)은 필수
  - law: "소득세법"
    article: "제55조"
    url: "https://www.law.go.kr/..."
    note: "선택"
reviewed_by: ["..."]              # 선택. 검수자
data: { ... }                     # 도구가 읽는 값
```

같은 연도에 시행일이 다른 버전이 여럿이면 파일을 나눈다.

```
kr_4insurance_2026.yaml               2026-01-01 ~ 2026-06-30
kr_4insurance_2026@2026-07-01.yaml    2026-07-01 ~ 2026-10-31
kr_4insurance_2026@2026-11-01.yaml    2026-11-01 ~ 2026-12-31
```

## 계산 시 버전 선택

정책 도구는 `year`와 함께 `as_of`, `include_proposed`를 받는다.

|호출|선택되는 버전|
|-|-|
|`as_of` 없음|그 연도 확정(enacted) 버전 중 시행일이 가장 늦은 것. 호출 날짜와 무관하다.|
|`as_of: "YYYY-MM-DD"`|그날이 시행 기간에 속하는 버전. `superseded` 버전도 자기 시행 기간에는 쓰인다.|
|`include_proposed: true`|개정안(`proposed`)까지 후보에 넣는다.|

후보가 없으면 오류를 낸다. 시행 중인 버전이 없으면 `policy_not_in_effect`(시행 기간 목록 포함), 그 연도에 개정안만 있으면 `policy_not_enacted`다.

응답에는 적용한 버전의 `policy_status`, `policy_effective_date`, `policy_effective_to`, `policy_citations`, `policy_sha256`이 붙고 영수증(`_meta.integrity`)에도 같은 정보가 들어간다. `as_of`와 `include_proposed`는 영수증의 입력 해시에 포함되므로 재실행 검증도 같은 버전으로 재현된다. 개정안으로 계산한 응답에는 `proposed_policy_in_use` 신호가 붙는다.

## 관리자 모드

정책을 바꾸는 쓰기 도구 4종(`policy_propose`, `policy_activate`, `policy_rollback`, `policy_import`)은 관리자 모드에서만 동작한다.

```bash
SOOTOOL_ADMIN_MODE=1 sootool        # 환경변수
sootool --admin                     # 또는 플래그
```

관리자 모드가 아니면 `{"error": "admin_required", "message": "..."}`를 돌려준다. 쓰기 도구는 stdio와 Unix 소켓에서만 노출된다. HTTP로 노출하려면 `--admin --remote-admin --admin-token <토큰>`이 모두 필요하고, 관리자 토큰으로 인증한 요청만 쓰기를 수행한다.

## 도구

|도구|관리자|하는 일|
|-|-|-|
|`sootool.policy_list`|아니오|정책 목록과 적용 저장소|
|`sootool.policy_get`|아니오|정책 본문 조회|
|`sootool.policy_history`|아니오|감사 기록 조회|
|`sootool.policy_diff`|아니오|두 버전의 의미 단위 차이|
|`sootool.policy_validate`|아니오|저장하지 않고 검증만|
|`sootool.policy_export`|아니오|이식용 번들 생성(선택적 서명)|
|`sootool.policy_propose`|예|초안 생성과 검증|
|`sootool.policy_activate`|예|초안을 덮어쓰기 저장소에 반영|
|`sootool.policy_rollback`|예|덮어쓰기를 지워 패키지 기본값으로 복귀|
|`sootool.policy_import`|예|번들 가져오기|

CLI에서는 `sootool policy <list|show|history|diff|validate|export|propose|activate|rollback|import>`로 같은 도구를 부른다.

## 연간 갱신 절차

```
고시문 확인 → policy_propose → 검증 보고서·전년 대비 차이 검토 → policy_activate → 계산 도구로 확인
                  │                                                    │
                  └─ 초안(24시간 유효)                                  └─ 덮어쓰기 저장소에 기록, 감사 로그 추가
```

1. 고시문이나 개정 법령을 확인하고 YAML 내용을 준비한다.
2. 초안을 만든다.
   ```
   policy_propose(domain="tax", name="kr_income", year=2027, yaml_content=...,
                  notice_no="소득세법 제55조제1항 ...",
                  source_url="https://www.law.go.kr/...",
                  effective_date="2027-01-01")
   ```
3. 응답의 검증 보고서와 전년 대비 차이를 검토한다.
4. 반영한다: `policy_activate(draft_id="drf-...")`. 검증 오류가 있는 초안은 `validation_failed`로 거부된다.
5. `tax.kr_income`을 불러 응답의 `policy_source`가 `override`인지 확인한다.

반영 규칙은 다음과 같다.

- 시행일이 기존 버전과 같으면 그 버전을 교체한다. 다르면 `@<시행일>` 버전 파일을 새로 만든다.
- 같은 연도 확정 버전끼리 시행 기간이 겹치면 안 된다(`policy_propose`, `policy_validate`가 검사). 새 버전을 넣기 전에 앞 버전의 `effective_to`를 닫는다.

## 검증 6단계

`policy_propose`와 `policy_validate`는 다음을 차례로 검사한다.

|단계|검사|
|-|-|
|1|안전한 YAML 파싱(`yaml.SafeLoader`, 파이썬 객체 태그 거부)|
|2|필수 헤더(`sha256`, `effective_date`, `notice_no`, `source_url`, `data`)와 v2 헤더 형식(`effective_to`, `status`, `citations` 등)|
|3|도메인별 구조 스키마(구간표, 세율 타입 등)|
|4|교차 검사: 구간 상한이 단조 증가, 마지막 상한은 null, 세율은 0 이상 1 이하, 같은 연도 확정 버전의 시행 기간 겹침|
|5|전년 대비 민감도: 세율 변화가 임계값을 넘으면 경고|
|6|SHA-256 무결성(`auto_fix_sha256=true`면 다시 계산해 채움)|

민감도 임계값은 호출 인자 `sensitivity_threshold`, 환경변수 `SOOTOOL_POLICY_DIFF_THRESHOLD`, 기본값 0.5(50%p) 순으로 정해진다.

## 초안

- 저장 위치: `$SOOTOOL_DRAFT_DIR`, 없으면 `$XDG_RUNTIME_DIR/sootool/drafts/`, 그것도 없으면 상태 디렉터리 아래 `drafts/`.
- 유효 기간 24시간. 만료된 초안은 불러올 때 지워지고 반영할 수 없다.
- 파일 권한 0600, 디렉터리 0700. 초안 ID 형식은 `drf-<uuid4 hex>`.

## 감사 로그

모든 쓰기는 JSON Lines 한 줄을 덧붙인다(파일 권한 0600).

```
$SOOTOOL_STATE_DIR/policy_audit.jsonl
$XDG_STATE_HOME/sootool/policy_audit.jsonl     (기본)
~/.local/state/sootool/policy_audit.jsonl
```

```json
{
  "ts":            "2026-04-23T09:00:00Z",
  "audit_id":      "aud-<hex>",
  "actor":         "user:cli",
  "action":        "activate",
  "domain":        "tax",
  "name":          "kr_income",
  "year":          2027,
  "draft_id":      "drf-<hex>",
  "sha256_before": "<이전 해시 또는 null>",
  "sha256_after":  "<새 해시>",
  "source_url":    "...",
  "notice_no":     "...",
  "validation":    {"status": "ok", "findings": []}
}
```

`policy_history(domain="tax", name="kr_income")`로 조회한다. 덮어쓰기 정책을 쓴 계산 응답에는 해당 `policy_audit_id`가 실린다.

## 롤백

```
policy_rollback(domain="tax", name="kr_income", year=2027)
```

덮어쓰기 파일을 지우고 로더 캐시를 비워 패키지 기본값으로 돌아간다. 같은 연도에 덮어쓰기 버전이 여럿이면 `effective_date`로 지울 버전을 지정한다. 롤백도 감사 로그에 남는다.

## 번들 서명

`policy_export(include_signature=true)`는 번들에 ed25519 서명을 붙인다. 개인 키는 `SOOTOOL_POLICY_KEY_FILE`이 가리키는 파일(base64 원시 개인 키, 권한 0600)에서 읽는다. 키는 도구 인자로 받지 않으므로 호출 기록에 남지 않는다.

`policy_import`는 `require_signature=true`이거나 `SOOTOOL_POLICY_REQUIRE_SIGNATURE=1`일 때 서명을 검증한다. 기본은 서명을 요구하지 않는다. 여러 번들을 하나로 묶어 배포하는 방법은 [external_policy_packs.md](external_policy_packs.md)를 본다.

## 패키지 정책을 직접 고친 경우

저장소의 정책 파일을 손으로 고쳤다면 자체 해시를 갱신한다. CI는 `--check`로 해시 불일치를 잡는다.

```bash
uv run python scripts/policy_stamp.py            # 모든 패키지 정책의 해시 갱신
uv run python scripts/policy_stamp.py --check    # 불일치가 있으면 종료 코드 1
```

## 보안

- 모든 쓰기는 임시 파일 작성 → fsync → rename으로 원자적으로 교체한다.
- 덮어쓰기 디렉터리는 0700, 파일은 0600으로 만든다.
- `source_url`은 메타데이터로만 저장하며 서버가 그 주소에 접속하지 않는다.
