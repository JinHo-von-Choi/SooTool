"""Tests for datetime.tz_convert tool."""
from __future__ import annotations

import sootool.modules.datetime_  # noqa: F401
from sootool.core.registry import REGISTRY


class TestTzConvert:
    def test_seoul_to_utc(self) -> None:
        """Seoul +09:00 2026-01-01T12:00:00 -> UTC 2026-01-01T03:00:00."""
        result = REGISTRY.invoke(
            "datetime.tz_convert",
            iso_datetime="2026-01-01T12:00:00",
            from_tz="Asia/Seoul",
            to_tz="UTC",
        )
        assert "2026-01-01T03:00:00" in result["iso_datetime"]
        assert "trace" in result

    def test_utc_to_seoul(self) -> None:
        """UTC 2026-01-01T00:00:00 -> Seoul +09:00."""
        result = REGISTRY.invoke(
            "datetime.tz_convert",
            iso_datetime="2026-01-01T00:00:00",
            from_tz="UTC",
            to_tz="Asia/Seoul",
        )
        assert "2026-01-01T09:00:00" in result["iso_datetime"]

    def test_dst_seoul_to_la_before_spring_forward(self) -> None:
        """Asia/Seoul has no DST. America/Los_Angeles spring forward 2026-03-08 2am.
        Seoul 2026-03-08 18:00 = UTC 09:00 = LA 01:00 PST (before spring forward).
        """
        result = REGISTRY.invoke(
            "datetime.tz_convert",
            iso_datetime="2026-03-08T18:00:00",
            from_tz="Asia/Seoul",
            to_tz="America/Los_Angeles",
        )
        dt_str = result["iso_datetime"]
        # Should be PST offset (-08:00)
        assert "2026-03-08T01:00:00" in dt_str
        assert "-08:00" in dt_str

    def test_dst_seoul_to_la_after_spring_forward(self) -> None:
        """Seoul 2026-03-08 19:00 = UTC 10:00 = LA 03:00 PDT (after spring forward).
        Offset changes from -08:00 to -07:00.
        """
        result = REGISTRY.invoke(
            "datetime.tz_convert",
            iso_datetime="2026-03-08T19:00:00",
            from_tz="Asia/Seoul",
            to_tz="America/Los_Angeles",
        )
        dt_str = result["iso_datetime"]
        # Should be PDT offset (-07:00) - spring forward happened
        assert "2026-03-08T03:00:00" in dt_str
        assert "-07:00" in dt_str

    def test_known_offset_passthrough(self) -> None:
        """Naive datetime with explicit from_tz."""
        result = REGISTRY.invoke(
            "datetime.tz_convert",
            iso_datetime="2026-06-01T12:00:00",
            from_tz="Europe/London",
            to_tz="Asia/Tokyo",
        )
        # London BST (UTC+1) in summer, Tokyo JST (UTC+9)
        # 12:00 BST = 11:00 UTC = 20:00 JST
        assert "2026-06-01T20:00:00" in result["iso_datetime"]

    def test_trace_fields(self) -> None:
        result = REGISTRY.invoke(
            "datetime.tz_convert",
            iso_datetime="2026-01-01T12:00:00",
            from_tz="Asia/Seoul",
            to_tz="UTC",
        )
        assert result["trace"]["tool"] == "datetime.tz_convert"
