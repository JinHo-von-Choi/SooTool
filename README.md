# SooTool

LLM 정밀 계산 MCP 서버. Decimal 커널 + 도메인 모듈 플러그인 아키텍처.

## 실행
- stdio: `uv run python -m sootool`
- HTTP: `uv run python -m sootool --transport http --port 10535`

## 개발
- 테스트: `make test`
- 린트: `make lint`
