from __future__ import annotations

_MIN_DESCRIPTION_CHARS = 30


def test_every_tool_has_a_substantive_description():
    from sootool import server as S
    from sootool.core.registry import REGISTRY

    S._load_modules()
    short = [
        e.full_name for e in REGISTRY.list()
        if len(e.description.strip()) < _MIN_DESCRIPTION_CHARS
    ]
    assert not short, short


_DESCRIPTION_RANGE = (60, 350)


def test_descriptions_stay_within_the_documented_length_range():
    from sootool import server as S
    from sootool.core.registry import REGISTRY

    S._load_modules()
    low, high = _DESCRIPTION_RANGE
    outside = [
        (e.full_name, len(" ".join(e.description.split()))) for e in REGISTRY.list()
        if not low <= len(" ".join(e.description.split())) <= high
    ]
    assert not outside, outside
