import json
from types import SimpleNamespace as NS

import pytest

import code_index.collections_commands as cc


class FakeQdrantClient:
    def __init__(self, collections, ws_map, scroll_payloads, points_map=None, cfgs=None):
        # collections: list of collection names
        # ws_map: mapping collection_name -> workspace_path (metadata)
        # scroll_payloads: mapping collection_name -> payload dict (for scroll probing)
        # points_map: mapping collection_name -> points_count
        # cfgs: mapping collection_name -> config object (dict-like)
        self._collections = collections
        self._ws_map = dict(ws_map or {})
        self._scroll_payloads = dict(scroll_payloads or {})
        self._points_map = dict(points_map or {})
        self._cfgs = dict(cfgs or {})

    def get_collections(self):
        return NS(collections=[NS(name=n) for n in self._collections])

    def get_collection(self, collection_name):
        points_count = int(self._points_map.get(collection_name, 0))
        cfg = self._cfgs.get(collection_name, {})
        # vectors_count rough heuristic for display only
        if isinstance(cfg, dict) and "vectors" in cfg and isinstance(cfg["vectors"], dict):
            vectors_count = len(cfg["vectors"])
        else:
            vectors_count = 1
        return NS(points_count=points_count, config=cfg, status="green", vectors_count=vectors_count)

    def query_points(self, collection_name, query=None, limit=None, with_payload=None, query_filter=None, **kwargs):
        # Metadata collection lookup
        if collection_name == "code_index_metadata":
            if query_filter is not None:
                # Attempt to parse Filter - FieldCondition - MatchValue
                try:
                    must = getattr(query_filter, "must", []) or []
                    for cond in must:
                        key = getattr(cond, "key", None)
                        match = getattr(cond, "match", None)
                        value = getattr(match, "value", None)
                        if key == "collection_name" and value in self._ws_map:
                            wp = self._ws_map[value]
                            return NS(points=[NS(payload={"collection_name": value, "workspace_path": wp})])
                except Exception:
                    pass
            # No filter: return all mapped items
            pts = [NS(payload={"collection_name": k, "workspace_path": v}) for k, v in self._ws_map.items()]
            return NS(points=pts[: (limit or len(pts))])
        # Fallback: empty
        return NS(points=[])

    def scroll(self, collection_name, limit=None, with_payload=None, with_vectors=None, **kwargs):
        payload = self._scroll_payloads.get(collection_name, {})
        return ([NS(payload=payload)], None)


def _patch_qdrant_client(monkeypatch, collections, ws_map, scroll_payloads, points_map=None, cfgs=None):
    import code_index.collections as col_mod

    def _factory(*args, **kwargs):
        return FakeQdrantClient(collections, ws_map, scroll_payloads, points_map=points_map, cfgs=cfgs)

    monkeypatch.setattr(col_mod, "QdrantClient", _factory)


def test_collections_list_shows_dim_and_model(monkeypatch, capsys):
    # Two collections: one with default vector size, one with named vectors
    collections = ["col1", "col2"]
    ws_map = {"col1": "/tmp/ws1", "col2": "/tmp/ws2"}
    points_map = {"col1": 10, "col2": 5}
    cfgs = {
        # default vector
        "col1": {"params": {"size": 768}},
        # named vectors
        "col2": {"vectors": {"text": {"size": 768}, "img": {"size": 512}}},
    }
    scroll_payloads = {
        "col1": {"embedding_model": "nomic-embed-text:v1.5"},
        "col2": {"embedding_model": "xxx:latest"},
    }

    _patch_qdrant_client(monkeypatch, collections, ws_map, scroll_payloads, points_map=points_map, cfgs=cfgs)

    # Run the CLI command function (call underlying callback)
    cc.list_collections.callback(detailed=True)
    out = capsys.readouterr().out

    # col1: default vector shows just size, and model remains as-is
    assert "col1" in out
    assert "768" in out
    assert "nomic-embed-text:v1.5" in out

    # col2: named vectors show "text:768,img:512", and model canonicalized to "xxx"
    assert "col2" in out
    assert "text:768,img:512" in out
    # Canonicalized model (strip ':latest')
    assert " xxx " in out or " xxx\n" in out or " xxx\t" in out or " xxx:" in out


def test_collection_info_shows_dim_and_model(monkeypatch, capsys):
    # Named vector collection with model identifier
    collections = ["col2"]
    ws_map = {"col2": "/tmp/ws2"}
    points_map = {"col2": 5}
    cfgs = {
        "col2": {"vectors": {"text": {"size": 768}, "img": {"size": 512}}},
    }
    scroll_payloads = {
        "col2": {"embedding_model": "xxx:latest"},
    }

    _patch_qdrant_client(monkeypatch, collections, ws_map, scroll_payloads, points_map=points_map, cfgs=cfgs)

    # Run the CLI command function (call underlying callback)
    cc.collection_info.callback("col2")
    out = capsys.readouterr().out

    # Should print named vectors each on its own line
    assert "Vector text: 768" in out
    assert "Vector img: 512" in out
    # Should print canonicalized model
    assert "Model: xxx" in out


def test_collections_list_legacy_model_unknown(monkeypatch, capsys):
    # Legacy collection without payload keys and no metadata fallback
    collections = ["legacy"]
    ws_map = {}  # no metadata for legacy
    points_map = {"legacy": 1}
    cfgs = {
        "legacy": {"params": {"size": 1024}},
    }
    scroll_payloads = {
        "legacy": {},  # no model keys
    }

    _patch_qdrant_client(monkeypatch, collections, ws_map, scroll_payloads, points_map=points_map, cfgs=cfgs)

    cc.list_collections.callback(detailed=True)
    out = capsys.readouterr().out

    assert "legacy" in out
    assert "1024" in out
    assert "unknown" in out


def test_collections_info_without_payload_model_shows_unknown(monkeypatch, capsys, tmp_path):
    # Collection with no model in payload; no fallback to local config anymore
    collections = ["cfgcol"]
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir(parents=True, exist_ok=True)

    ws_map = {"cfgcol": str(ws_dir)}
    points_map = {"cfgcol": 2}
    cfgs = {
        "cfgcol": {"params": {"size": 384}},
    }
    scroll_payloads = {
        "cfgcol": {},  # no model keys -> should remain 'unknown'
    }

    _patch_qdrant_client(monkeypatch, collections, ws_map, scroll_payloads, points_map=points_map, cfgs=cfgs)

    cc.collection_info.callback("cfgcol")
    out = capsys.readouterr().out

    # Without payload model and no fallback, model should be 'unknown'
    assert "Model: unknown" in out
    # Dimension single default displays as "Dimension: 384"
    assert "Dimension: 384" in out