from live.universe_store import UniverseEntry, UniverseStore


def test_default_universe_empty():
    s = UniverseStore(entries=[])
    assert s.entries == []


def test_add_remove(tmp_path):
    s = UniverseStore(entries=[])
    s.add(UniverseEntry(name="TIGER 미국S&P500", code="360750"))
    s.add(UniverseEntry(name="TIGER 미국테크TOP10 INDXX", code="381170"))
    assert len(s.entries) == 2
    s.remove("360750")
    assert len(s.entries) == 1 and s.entries[0].code == "381170"


def test_add_dup_code_replaces(tmp_path):
    s = UniverseStore(entries=[UniverseEntry("OLD", "360750")])
    s.add(UniverseEntry(name="NEW", code="360750"))
    assert len(s.entries) == 1
    assert s.entries[0].name == "NEW"


def test_roundtrip(tmp_path):
    s = UniverseStore(entries=[UniverseEntry("A", "111"),
                                UniverseEntry("B", "222")])
    p = tmp_path / "u.json"
    s.save(p)
    s2 = UniverseStore.load(p)
    assert [(e.name, e.code) for e in s2.entries] == [("A", "111"),
                                                       ("B", "222")]


def test_load_missing_returns_empty(tmp_path):
    s = UniverseStore.load(tmp_path / "no.json")
    assert s.entries == []


def test_codes_helper():
    s = UniverseStore(entries=[UniverseEntry("A", "111"),
                                UniverseEntry("B", "222")])
    assert s.codes() == ["111", "222"]
