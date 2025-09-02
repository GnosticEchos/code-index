import pytest

import code_index.collections_commands as cc
import code_index.cache as cache_mod


def test_metadata_lookup_scroll_tuple(monkeypatch, capsys):
    class DummyClient:
        # Accept arbitrary args/kwargs to tolerate signature variance
        def scroll(self, *args, **kwargs):
            return ([{"payload": {"collection_name": "ws-abc", "workspace_path": "/abs/path"}}], None)

    class DummyManager:
        def __init__(self, cfg):
            self.client = DummyClient()

        def get_collection_info(self, collection_name):
            return {
                "name": collection_name,
                "status": "green",
                "points_count": 0,
                "vectors_count": 0,
                "dimensions": {},
                "model_identifier": "unknown",
            }

    monkeypatch.setattr(cc, "CollectionManager", DummyManager)

    cc.collection_info.callback("ws-abc")
    out = capsys.readouterr().out
    assert "Workspace Path: /abs/path" in out


def test_metadata_lookup_scroll_object_points(monkeypatch, capsys):
    class DummyPoint:
        def __init__(self):
            self.payload = {"collection_name": "ws-xyz", "workspace_path": "/root/ws"}

    class DummyScrollRes:
        def __init__(self):
            self.points = [DummyPoint()]

    class DummyClient:
        def scroll(self, *args, **kwargs):
            return DummyScrollRes()

    class DummyManager:
        def __init__(self, cfg):
            self.client = DummyClient()

        def get_collection_info(self, collection_name):
            return {
                "name": collection_name,
                "status": "green",
                "points_count": 0,
                "vectors_count": 0,
                "dimensions": {},
                "model_identifier": "unknown",
            }

    monkeypatch.setattr(cc, "CollectionManager", DummyManager)

    cc.collection_info.callback("ws-xyz")
    out = capsys.readouterr().out
    assert "Workspace Path: /root/ws" in out


def test_discovery_failure_should_exit_and_not_clear_cache(monkeypatch):
    class DummyClient:
        def get_collections(self):
            raise RuntimeError("network down")

    class DummyManager:
        def __init__(self, cfg):
            self.client = DummyClient()

    called = {"flag": False}

    def fake_clear_all_caches(config=None):
        called["flag"] = True
        return 0

    monkeypatch.setattr(cc, "CollectionManager", DummyManager)
    monkeypatch.setattr(cache_mod, "clear_all_caches", fake_clear_all_caches)

    with pytest.raises(SystemExit) as ectx:
        cc.clear_all_collections.callback(yes=True, dry_run=False, keep_metadata=False)
    assert ectx.value.code == 1
    assert called["flag"] is False


def test_already_absent_path_counter_verification(monkeypatch, capsys):
    class DummyClient:
        def get_collections(self):
            return ["ws-1", "ws-2"]

        def delete_collection(self, name):
            if name == "ws-1":
                raise Exception("404 not found")
            if name == "ws-2":
                return True
            raise Exception("unexpected collection name")

    class DummyManager:
        def __init__(self, cfg):
            self.client = DummyClient()

    monkeypatch.setattr(cc, "CollectionManager", DummyManager)
    monkeypatch.setattr(cache_mod, "clear_all_caches", lambda config=None: 0)

    cc.clear_all_collections.callback(yes=True, dry_run=False, keep_metadata=False)
    out = capsys.readouterr().out
    assert "already absent 1" in out
    assert "deleted 1" in out
    assert "failed 0" in out