# SooTool 벤치마크 리트머스 결과 — YYYY-MM-DD (템플릿)

이 파일은 `bench/run_benchmark.py` 가 자동 생성하는 결과의 구조를 보여주는
템플릿이다. 실제 실행 결과는 `YYYY-MM-DD.md` 형식으로 동일 디렉토리에 저장된다.

분류: `exact` 문자열 일치, `approx` 상대오차 ≤ 0.01%, `wrong` 그 외,
`no_answer` 응답 없음, `skip` SDK 미설치·API 키 미설정.

## 종합 표

|id|expected|sootool|openai|anthropic|google|
|-|-|-|-|-|-|
|tax_kr_income_14M|840000|exact|exact (840000)|exact (840000)|exact (840000)|
|...|...|...|...|...|...|

## 집계

|provider|exact|approx|wrong|no_answer|skip|
|-|-|-|-|-|-|
|sootool|20|0|0|0|0|
|openai|?|?|?|?|?|
|anthropic|?|?|?|?|?|
|google|?|?|?|?|?|

## 상세 로그

### <case_id> (<category>, <difficulty>)

- expected: `...`
- sootool: `...` (exact)
- openai (<model>): `...` class — raw=`...`
- anthropic (<model>): `...` class — raw=`...`
- google (<model>): `...` class — raw=`...`
