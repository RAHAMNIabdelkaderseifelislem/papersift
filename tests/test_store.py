import pytest

from papersift.store import Store


def test_get_unknown_returns_none():
    with Store(":memory:", "project") as store:
        assert store.get("1234") is None


def test_upsert_and_get_round_trip_with_json_columns():
    with Store(":memory:", "project") as store:
        store.upsert("1", title="T", abstract_assessment={"score": 70})
        row = store.get("1")
        assert row["title"] == "T" and row["abstract_assessment"] == {"score": 70}
        assert row["fulltext_assessment"] is None


def test_upsert_updates_only_given_fields():
    with Store(":memory:", "project") as store:
        store.upsert("1", title="T", abstract_assessment={"score": 70})
        store.upsert("1", final_score=88)
        row = store.get("1")
        assert row["final_score"] == 88 and row["title"] == "T"
        assert row["abstract_assessment"] == {"score": 70}


def test_unknown_column_rejected():
    with Store(":memory:", "project") as store, pytest.raises(ValueError):
        store.upsert("1", bogus=1)


def test_cache_is_separate_per_project(tmp_path):
    db = tmp_path / "cache.sqlite3"
    with Store(db, "Project A") as a:
        a.upsert("1", title="T")
    with Store(db, "Project B") as b:
        assert b.get("1") is None
    with Store(db, " project a ") as a_again:  # same project, different case/spaces
        assert a_again.get("1")["title"] == "T"
