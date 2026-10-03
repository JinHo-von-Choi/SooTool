from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from sootool.core.lazy import lazy_module


def test_proxy_resolves_attribute_from_real_module():
    json_proxy = lazy_module("json")
    assert json_proxy.dumps({"a": 1}) == '{"a": 1}'


def test_proxy_does_not_import_until_first_access():
    name = "this_module_does_not_exist_anywhere"
    proxy = lazy_module(name)
    assert name not in sys.modules
    with pytest.raises(ModuleNotFoundError):
        getattr(proxy, "anything")  # noqa: B009


def test_proxy_repr_names_the_target_module():
    assert "json" in repr(lazy_module("json"))


def test_heavy_statistics_modules_are_not_loaded_at_startup():
    script = textwrap.dedent(
        """
        import sys
        from sootool import server
        server._load_modules()
        server.build_server()
        heavy = [m for m in ("scipy.stats", "scipy.interpolate", "statsmodels.api") if m in sys.modules]
        print(",".join(heavy))
        """
    )
    out = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script], capture_output=True, text=True, check=True, timeout=120,
    )
    assert out.stdout.strip() == ""


def test_lazy_modules_work_on_first_tool_call():
    from sootool import server
    from sootool.core.registry import REGISTRY

    server._load_modules()
    result = REGISTRY.invoke("stats.ci_mean", values=["1", "2", "3", "4", "5"])
    assert result["mean"] == "3"
    result = REGISTRY.invoke("probability.f_cdf", x="1", dfn="5", dfd="5")
    assert result["result"]
