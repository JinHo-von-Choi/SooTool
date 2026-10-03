"""CLI 종료 코드."""
from __future__ import annotations

from typing import Final

OK:             Final = 0
TOOL_ERROR:     Final = 1   # 도구가 오류를 냄(도메인 제약, 정책 없음, 한도 초과 등)
INPUT_ERROR:    Final = 2   # 사용법, 인자 형식, 알 수 없는 도구
ADMIN_DENIED:   Final = 3   # 관리자 모드가 아니어서 쓰기 도구를 거부함
INTERNAL_ERROR: Final = 70  # 예기치 못한 내부 오류
