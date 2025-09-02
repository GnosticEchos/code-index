import logging
from pathlib import Path

import pytest


def _make_file(p: Path, content: str = "x") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


@pytest.mark.parametrize("canon_id", ["23361cfdcfce89e8"])
def test_single_collection_delete_cache_cleanup(monkeypatch, tmp_path: Path, caplog, canon_id: str):
    # Arrange: point the cache resolver to a temporary directory
    import code_index.cache as cache_mod
    monkeypatch.setattr(cache_mod, "resolve_cache_dir", lambda config=None: tmp_path)

    # Prepare cache files in the temp cache directory
    target = tmp_path / f"cache_{canon_id}.json"
    other = tmp_path / "cache_other.json"
    _make_file(target, '{"ok":true}')
    _make_file(other, '{"ok":true}')

    # Monkeypatch canonical id resolver to avoid any backend calls
    import code_index.collections_commands as cc
    monkeypatch.setattr(cc, "_resolve_canonical_id_for_delete", lambda cm, name: canon_id)

    # Avoid interactive prompt and backend deletion side effects
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")

    class DummyCollectionManager:
        def __init__(self, cfg):
            pass
        def delete_collection(self, collection_name: str):
            return True

    # Replace CollectionManager with dummy to avoid constructing real Qdrant client
    monkeypatch.setattr(cc, "CollectionManager", DummyCollectionManager)

    # Capture INFO logs from cache helpers
    caplog.set_level(logging.INFO, logger="code_index.cache")

    # Act: call the click command's underlying callback directly
    # Using the collection name pattern "ws-<hex16>" is fine, but our resolver is already patched
    cc.delete_collection.callback(f"ws-{canon_id}")

    # Assert: targeted cache file removed, unrelated remains
    assert not target.exists(), "Expected targeted cache file to be removed"
    assert other.exists(), "Unrelated cache file should remain"

    # Assert: INFO logs mention 1 file removed
    msgs = "\n".join(r.message for r in caplog.records if r.name == "code_index.cache")
    assert "removed 1 file(s) for collection id" in msgs


def test_global_clear_cache_cleanup(monkeypatch, tmp_path: Path, caplog):
    # Arrange: point the cache resolver to a temporary directory
    import code_index.cache as cache_mod
    monkeypatch.setattr(cache_mod, "resolve_cache_dir", lambda config=None: tmp_path)

    # Prepare multiple cache files and unrelated files
    c1 = tmp_path / "cache_1111111111111111.json"
    c2 = tmp_path / "cache_2222222222222222.json"
    c3 = tmp_path / "cache_aaaaaaaaaaaaaaaa.json"
    unrelated_txt = tmp_path / "notes.txt"
    unrelated_cache_named = tmp_path / "random_cache.txt"
    for p in [c1, c2, c3, unrelated_txt, unrelated_cache_named]:
        _make_file(p, "data")

    # Monkeypatch the CollectionManager in collections_commands to avoid any Qdrant connectivity
    import code_index.collections_commands as cc

    class DummyClient:
        def get_collections(self):
            # Include metadata to verify default deletion path includes it
            return ["ws-1111111111111111", "ws-2222222222222222", "code_index_metadata"]
        def delete_collection(self, name: str):
            return True

    class DummyCollectionManager:
        def __init__(self, cfg):
            self.client = DummyClient()

    monkeypatch.setattr(cc, "CollectionManager", DummyCollectionManager)

    # Capture INFO logs from cache helpers
    caplog.set_level(logging.INFO, logger="code_index.cache")

    # Act: call collections clear-all command's underlying callback directly
    cc.clear_all_collections.callback(yes=True, dry_run=False, keep_metadata=False)

    # Assert: all cache_*.json files removed, unrelated files remain
    remaining_cache = list(tmp_path.glob("cache_*.json"))
    assert remaining_cache == [], f"Expected all cache_*.json files removed, found: {remaining_cache}"
    assert unrelated_txt.exists(), "Unrelated .txt file should remain"
    assert unrelated_cache_named.exists(), "Unrelated file that only contains 'cache' in name should remain"

    # Assert: INFO logs mention correct count removed
    msgs = "\n".join(r.message for r in caplog.records if r.name == "code_index.cache")
    # We created 3 cache_*.json files
    assert "removed 3 file(s) from" in msgs

def test_clear_all_dry_run(monkeypatch, tmp_path: Path, caplog):
    # Arrange: route cache dir to temp and prepare cache files that should NOT be deleted
    import code_index.cache as cache_mod
    monkeypatch.setattr(cache_mod, "resolve_cache_dir", lambda config=None: tmp_path)

    c1 = tmp_path / "cache_deadbeefdeadbeef.json"
    c2 = tmp_path / "cache_feedfeedfeedfeed.json"
    _make_file(c1, "data")
    _make_file(c2, "data")

    # Dummy manager to avoid backend calls; should not be used for deletion under --dry-run
    import code_index.collections_commands as cc

    class DummyClient:
        called = False
        def get_collections(self):
            return ["ws-deadbeefdeadbeef", "code_index_metadata"]
        def delete_collection(self, name: str):
            DummyClient.called = True
            return True

    class DummyCollectionManager:
        def __init__(self, cfg):
            self.client = DummyClient()

    monkeypatch.setattr(cc, "CollectionManager", DummyCollectionManager)

    # Capture INFO logs
    caplog.set_level(logging.INFO, logger="code_index.cache")

    # Act: dry run should not delete collections nor cache files
    cc.clear_all_collections.callback(yes=True, dry_run=True, keep_metadata=False)

    # Assert: cache files remain
    assert c1.exists() and c2.exists(), "Dry run should not delete any cache files"
    # Assert: no deletion attempts happened
    assert DummyClient.called is False, "Dry run should not call delete_collection()"


def test_clear_all_keep_metadata(monkeypatch, tmp_path: Path):
    # Arrange: monkeypatch a dummy CollectionManager and record calls
    import code_index.collections_commands as cc
    deleted: list[str] = []

    class DummyClient:
        def get_collections(self):
            return ["ws-1111111111111111", "code_index_metadata", "ws-2222222222222222"]
        def delete_collection(self, name: str):
            deleted.append(name)
            return True

    class DummyCollectionManager:
        def __init__(self, cfg):
            self.client = DummyClient()

    monkeypatch.setattr(cc, "CollectionManager", DummyCollectionManager)

    # Also route cache dir to tmp (no files needed)
    import code_index.cache as cache_mod
    monkeypatch.setattr(cache_mod, "resolve_cache_dir", lambda config=None: tmp_path)

    # Act: run with --keep-metadata
    cc.clear_all_collections.callback(yes=True, dry_run=False, keep_metadata=True)

    # Assert: metadata was excluded from deletion targets
    assert "code_index_metadata" not in deleted, "Metadata collection should be preserved under --keep-metadata"
    assert set(deleted) == {"ws-1111111111111111", "ws-2222222222222222"}, "All non-metadata collections should be deleted"