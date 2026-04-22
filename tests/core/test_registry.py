from sootool.core.registry import ToolRegistry


def test_registry_collects_tools():
    r = ToolRegistry()

    @r.tool(namespace="core", name="add", description="adds ints")
    def _add(a: int, b: int) -> int:
        return a + b

    entries = r.list()
    assert len(entries) == 1
    assert entries[0].full_name == "core.add"
    assert entries[0].description == "adds ints"


def test_registry_rejects_duplicate():
    r = ToolRegistry()

    @r.tool(namespace="x", name="f")
    def _f():
        return 1

    try:
        @r.tool(namespace="x", name="f")
        def _g():
            return 2
    except ValueError as e:
        assert "중복" in str(e)
    else:
        raise AssertionError("중복 미검출")


def test_registry_invokes():
    r = ToolRegistry()

    @r.tool(namespace="m", name="double")
    def _d(x: int) -> int:
        return x * 2

    assert r.invoke("m.double", x=5) == 10


def test_tool_entry_version_default():
    r = ToolRegistry()

    @r.tool(namespace="core", name="noop", description="noop")
    def _noop():
        pass

    entry = r.list()[0]
    assert entry.version == "1.0.0"


def test_tool_entry_version_custom():
    r = ToolRegistry()

    @r.tool(namespace="core", name="v2tool", description="v2 tool", version="2.0.0")
    def _v2():
        pass

    entry = r.list()[0]
    assert entry.version == "2.0.0"


def test_tool_entry_deprecated_none_by_default():
    r = ToolRegistry()

    @r.tool(namespace="core", name="current")
    def _current():
        pass

    entry = r.list()[0]
    assert entry.deprecated is None


def test_tool_entry_deprecated_dict():
    r = ToolRegistry()

    dep = {"since": "1.5.0", "replacement": "core.new", "sunset_date": "2026-12-31"}

    @r.tool(namespace="core", name="old", deprecated=dep)
    def _old():
        pass

    entry = r.list()[0]
    assert entry.deprecated == dep


def test_list_returns_deprecated_tools():
    r = ToolRegistry()

    @r.tool(namespace="core", name="active")
    def _active():
        pass

    @r.tool(
        namespace="core",
        name="legacy",
        deprecated={"since": "1.0.0", "replacement": "core.active", "sunset_date": "2026-06-01"},
    )
    def _legacy():
        pass

    entries = r.list()
    names = [e.full_name for e in entries]
    assert "core.active" in names
    assert "core.legacy" in names
    assert len(entries) == 2
