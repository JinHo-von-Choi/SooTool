# sootool.skill_guide 도구 레퍼런스

작성일: 2026-04-23

## 개요

`sootool.skill_guide`는 LLM 에이전트가 SooTool 도구 집합을 능동적으로 활용하도록 돕는 메타 도구다.
트리거 테이블, 실전 예시, 안티패턴 카탈로그, 플레이북을 구조화된 JSON으로 반환한다.

## 시그니처

```
sootool.skill_guide(
    section: str = "all",
    lang:    str | None = None
) -> dict
```

### 인자

| 인자 | 타입 | 기본값 | 설명 |
|-|-|-|-|
| section | str | "all" | 반환할 섹션. triggers / examples / anti_patterns / playbooks / all |
| lang | str \| None | None | 로캘 강제. None이면 자동 감지 |

### lang 자동 감지 우선순위

1. 호출 인자 `lang`
2. `Accept-Language` 헤더 (HTTP 전송 시)
3. 환경변수 `SOOTOOL_LOCALE`
4. 기본값 `ko`

지원 로캘: `ko`, `en`. 미지원 로캘은 `ko` fallback.

## 반환 구조

```json
{
  "version":       "1.0.0",
  "locale":        "ko",
  "triggers":      [...],
  "examples":      [...],
  "anti_patterns": [...],
  "playbooks":     [...]
}
```

섹션 필터 적용 시 해당 키만 포함된다.

## 트리거 테이블 근거

각 트리거 항목은 `signal` / `tool` / `reason` 세 필드로 구성된다.

- `signal`: LLM이 사용자 요청에서 감지해야 할 패턴
- `tool`: 즉시 호출해야 할 도구 이름
- `reason`: 도구 호출이 필요한 기술적 근거

| Signal | 근거 |
|-|-|
| 사칙연산 | LLM 확률 추론은 큰 수·소수점에서 오차 발생 |
| 세액·소득세·양도세 | 연도별 세율표 버전 고정 필요 |
| 부가세·공급가액 | 법정 DOWN 반올림 표준 |
| NPV·IRR·할인율 | Decimal 복리 정확도 |
| 영업일·공휴일 | holidays 라이브러리 법정 공휴일 |
| t-검정·신뢰구간 | scipy 수치 안정성 |

## 버전 관리

`version` 필드는 SemVer 형식이다.

- PATCH: 설명문·예시 보완
- MINOR: 트리거 추가, 플레이북 추가
- MAJOR: 기존 필드 의미 변경, 반환 구조 변경

ADR-012(도구 스키마 버전 관리) 규칙을 따른다.

## 사용 예시

```python
# 세션 시작 시 전체 가이드 로드
guide = sootool.skill_guide()

# 트리거 테이블만 영어로
triggers = sootool.skill_guide(section="triggers", lang="en")

# 플레이북 조회
playbooks = sootool.skill_guide(section="playbooks")
pb = next(pb for pb in playbooks["playbooks"] if pb["id"] == "payroll_to_net")
```

## 관련 ADR

- ADR-015: 에이전트 능동 활용 가이드 시스템
- ADR-012: MCP 도구 스키마 버전 관리
- ADR-011: Determinism 기본값 (`_meta.hints`는 result/trace 미변경)
