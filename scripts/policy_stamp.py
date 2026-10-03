"""정책 YAML 의 자체 해시(sha256 선언 줄)를 계산해 갱신하거나 검사한다.

정책 파일을 고친 뒤에는 선언된 sha256 이 본문과 맞아야 로더가 읽는다. 해시는 ``sha256:`` 줄을
뺀 본문의 SHA-256 이다.

사용:
    uv run python scripts/policy_stamp.py                      # 패키지 정책 전체 갱신
    uv run python scripts/policy_stamp.py path/to/policy.yaml  # 지정 파일 갱신
    uv run python scripts/policy_stamp.py --check              # 갱신 없이 불일치만 검사(불일치 시 종료 코드 1)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from sootool.policies import _compute_sha256

_SHA_LINE = re.compile(r'^sha256:.*\n', re.MULTILINE)
_POLICY_ROOT = Path(__file__).resolve().parents[1] / "src" / "sootool" / "policies"


def _stamp(text: str) -> str:
    digest = _compute_sha256(text)
    line   = f'sha256: "{digest}"\n'
    if _SHA_LINE.search(text):
        return _SHA_LINE.sub(line, text, count=1)
    return line + text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path, help="대상 정책 YAML (기본: 패키지 정책 전체)")
    parser.add_argument("--check", action="store_true", help="갱신하지 않고 불일치만 검사한다")
    args = parser.parse_args()

    paths = args.paths or sorted(_POLICY_ROOT.glob("*/*.yaml"))
    stale = 0
    for path in paths:
        text    = path.read_text(encoding="utf-8")
        updated = _stamp(text)
        if updated == text:
            continue
        stale += 1
        if args.check:
            print(f"MISMATCH {path}")
        else:
            path.write_text(updated, encoding="utf-8")
            print(f"stamped  {path}")
    if args.check and stale:
        return 1
    print(f"{len(paths)} files checked, {stale} {'mismatched' if args.check else 'updated'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
