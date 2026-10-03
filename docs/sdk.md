# SDK와 코드 실행 환경

`sootool.sdk` 는 MCP 서버 없이 SooTool 의 계산 도구를 파이썬 함수로 호출하는 라이브러리 인터페이스다. 코드 실행
환경(에이전트가 샌드박스에서 파이썬을 실행하는 구성)이 직접 산수를 하지 않고 감사된 규칙 라이브러리를 부르게 하는 것이
목적이다.

## 설치와 첫 호출

```bash
pip install sootool
```

```python
from sootool.sdk import tax, payroll, core

out = tax.kr_income(taxable_income=50_000_000, year=2026)
out["tax"]                                   # "6240000"
out["_meta"]["integrity"]["input_hash"]      # 입력과 결과의 영수증

net = payroll.kr_salary(monthly_salary="3500000", year=2026, num_dependents=1)
net["net"]
```

- 네임스페이스(`tax`, `payroll`, `realestate`, `finance`, `stats` 등)는 처음 쓸 때 해당 도메인만 불러온다. `mcp` 패키지를
  가져오지 않으므로 도메인 하나를 쓰는 데 약 0.5초가 든다.
- 결과는 MCP 응답과 같은 구조다. 계산 결과 필드, `trace`, `_meta.integrity` 가 있고 정책 도구는 적용된 정책의 출처와 근거
  조문(`policy_citations`)이 함께 온다.
- 오류는 `sootool.core.errors.SooToolError` 계열 예외로 발생한다(`InvalidInputError`, `DivisionByZeroError`,
  `PolicyNotInEffectError` 등). 각 예외의 `to_payload()` 가 MCP 오류 계약과 같은 코드와 메시지를 준다.

## 숫자 인자

문자열 숫자를 받는 파라미터는 정수, `Decimal`, 부동소수도 받는다. 정수와 `Decimal` 은 그대로 문자열이 되고, 부동소수는
배정밀도 최단 표기로 바뀌며 응답의 `_meta.input_coerced` 에 인자 이름과 변환값이 기록된다. 배정밀도를 넘는 자릿수가 필요하면
처음부터 문자열로 넘긴다. `year: int` 처럼 정수를 받는 파라미터는 바꾸지 않는다.

## 타입

모든 도구는 결과를 TypedDict 로 선언한다. 타입 검사기와 편집기는 `sootool/sdk/_typed.py` 로 시그니처와 결과 필드를 본다.

```python
from sootool.sdk import tax

out = tax.kr_income(taxable_income=1, year="2026")   # mypy: Argument "year" ... expected "int"
reveal_type(tax.kr_income(taxable_income=1, year=2026)["tax"])   # str
```

타입 선언 파일은 `uv run python scripts/gen_sdk_stubs.py` 가 레지스트리에서 생성하며, 시험이 최신 여부를 검사한다.

## 코드 실행 환경에서의 사용 레시피

1. 샌드박스 이미지에 `pip install sootool` 을 포함한다(`sootool[symbolic]` 은 기호 계산 도구가 필요할 때만).
2. 에이전트 프롬프트에 규칙을 적는다: 세금, 금융, 통계 등 수치 계산은 직접 하지 말고 `from sootool.sdk import <도메인>` 으로
   호출하고, 결과의 `trace` 와 `_meta.integrity` 를 사용자 답변에 인용한다.
3. 도구 탐색은 `dir(sdk.tax)` 로 이름을, `help(sdk.tax.kr_income)` 로 설명과 인자를 본다. 네임스페이스 목록은 `sdk.namespaces()`.
4. 여러 시나리오는 파이썬 반복문으로 호출하거나 `core.batch(items=[...])` 를 쓴다. 앞 결과를 뒤 입력에 넘기는 흐름은 변수로
   직접 이어도 되고 `core.pipeline` 으로 묶어 영수증에 남길 수도 있다.
5. 감사가 필요하면 `_meta.integrity` 를 저장하고 `sootool receipt verify` 또는 `sootool.verify_receipt` 도구로 재실행 검증한다.
   서명 키가 있으면(`SOOTOOL_RECEIPT_KEY_FILE`) 영수증에 ed25519 서명이 붙는다.

## MCP 와의 차이

| 항목 | MCP | SDK |
|-|-|-|
| 호출 경로 | 서버를 거쳐 `REGISTRY.invoke` | `REGISTRY.invoke` 직접 |
| 오류 | `isError` 결과와 오류 계약 | 예외 |
| 인자 검증 | 입력 스키마(pydantic) | 시그니처 바인딩 후 도구 내부 검증 |
| 기동 비용 | 서버 프로세스(약 2.2~2.6초) | 도메인 import(약 0.5초) |
| 쓰기 도구(정책 관리) | 관리자 모드와 범위 필요 | 같은 관리자 게이트(`SOOTOOL_ADMIN_MODE`) |
