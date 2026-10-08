# 파이썬 라이브러리 (sootool.sdk)

`sootool.sdk`는 MCP 서버 없이 SooTool 도구를 파이썬 함수로 부르는 인터페이스다. 에이전트가 샌드박스에서 파이썬 코드를 실행하는 구성이라면, 코드 안에서 직접 산수를 하지 말고 이 라이브러리를 부르게 한다. 결과에는 MCP와 같은 `trace`와 영수증이 붙는다.

## 설치와 첫 호출

```bash
pip install sootool
```

```python
from sootool.sdk import tax, payroll

out = tax.kr_income(taxable_income=50_000_000, year=2026)
out["tax"]                                # "6240000"
out["_meta"]["integrity"]["input_hash"]   # 영수증

net = payroll.kr_salary(monthly_salary="3500000", year=2026, num_dependents=1)
net["net"]                                # "3019958"
```

- 네임스페이스(`tax`, `payroll`, `finance`, `stats` 등)는 처음 쓸 때 그 도메인만 불러온다. `mcp` 패키지를 가져오지 않아 첫 호출까지 약 0.35~0.5초가 걸린다.
- 결과 구조는 MCP 응답과 같다. 결과 필드, `trace`, `_meta.integrity`가 있고, 정책 도구는 근거 조문(`policy_citations`)이 함께 온다.
- 정책 도구는 MCP와 같이 `as_of`, `include_proposed`를 받는다.

## 숫자 인자

숫자 문자열을 받는 인자에는 `int`, `Decimal`, `float`도 넘길 수 있다.

|넘긴 값|처리|
|-|-|
|`int`, `Decimal`|그대로 문자열로 바꾼다.|
|`float`|배정밀도 최단 표기로 바꾸고, 응답 `_meta.input_coerced`에 인자 이름과 변환값을 기록한다.|
|`str`|그대로 쓴다. 배정밀도를 넘는 자릿수가 필요하면 문자열로 넘긴다.|

`year: int`처럼 정수로 선언된 인자는 바꾸지 않는다.

## 오류

오류는 `sootool.core.errors.SooToolError` 계열 예외로 올라온다(`InvalidInputError`, `DivisionByZeroError`, `PolicyNotInEffectError` 등). `exc.to_payload()`는 MCP 오류와 같은 `code`, `message`, `retryable`을 돌려준다.

```python
from sootool.core.errors import SooToolError

try:
    tax.kr_income(taxable_income="-1", year=2026)
except SooToolError as exc:
    print(exc.to_payload()["code"])
```

## 타입

모든 도구의 결과가 TypedDict로 선언되어 있어 mypy와 편집기가 인자와 결과 필드를 확인한다.

```python
out = tax.kr_income(taxable_income=1, year="2026")   # mypy: Argument "year" ... expected "int"
reveal_type(tax.kr_income(taxable_income=1, year=2026)["tax"])   # str
```

타입 선언 파일 `sootool/sdk/_typed.py`는 `uv run python scripts/gen_sdk_stubs.py`가 레지스트리에서 생성한다.

## 샌드박스 구성

1. 샌드박스 이미지에 `pip install sootool`을 넣는다. 기호 계산이 필요하면 `sootool[symbolic]`.
2. 에이전트 지시문에 규칙을 적는다. 예: "세금, 금융, 통계 등 수치 계산은 직접 하지 말고 `from sootool.sdk import <도메인>`으로 호출한다. 답변에는 결과의 `trace`를 근거로 인용한다."
3. 도구 탐색: `sdk.namespaces()`로 네임스페이스 목록, `dir(sdk.tax)`로 도구 이름, `help(sdk.tax.kr_income)`으로 설명과 인자를 본다.
4. 여러 시나리오는 파이썬 반복문으로 부르거나 `core.batch(items=[...])`를 쓴다. 앞 결과를 뒤 입력에 넘길 때는 변수로 이어도 되고, 하나의 영수증으로 남기고 싶으면 `core.pipeline`으로 묶는다.
5. 감사가 필요하면 `_meta.integrity`를 저장해 두고 `sootool receipt verify`나 `sootool.verify_receipt`로 재실행 검증한다. `SOOTOOL_RECEIPT_KEY_FILE`에 ed25519 개인 키 파일을 지정하면 영수증에 서명이 붙는다.

## MCP와의 차이

|항목|MCP|SDK|
|-|-|-|
|오류|`isError` 결과|예외|
|인자 검증|입력 스키마|함수 시그니처와 도구 내부 검증|
|기동 비용|서버 프로세스 약 1.7~2.0초|도메인 하나 불러와 첫 호출까지 약 0.35~0.5초|
|정책 쓰기 도구|관리자 모드와 쓰기 권한 필요|관리자 모드(`SOOTOOL_ADMIN_MODE=1`) 필요|

결과, 영수증, 정책 버전 선택은 같은 레지스트리를 거치므로 동일하다.
