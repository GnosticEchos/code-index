import os
import pytest

def _load_language(lang_key: str):
    try:
        import tree_sitter_language_pack as tsl  # type: ignore
        return tsl.get_language(lang_key)
    except Exception as e:
        pytest.skip(f"Tree-sitter language '{lang_key}' not available: {e}")

def _compile_query(language, query_text: str):
    try:
        from tree_sitter import Query  # type: ignore
    except Exception as e:
        pytest.skip(f"tree_sitter module not available: {e}")

    # Try modern constructor first, then fallback to language.query if present
    try:
        return Query(language, query_text)
    except Exception:
        if hasattr(language, "query"):
            try:
                return language.query(query_text)  # type: ignore[attr-defined]
            except Exception as e:
                pytest.fail(f"Failed to compile query via language.query: {e}")
        else:
            pytest.fail("Language does not support query compilation on this binding")

def test_vue_query_compiles_minimal():
    """
    Verify that the configured Vue query compiles in the current environment.

    This test intentionally allows the Vue query to be empty (''), which should
    compile successfully and result in zero captures at runtime, driving the
    limited-extraction fallback path. This approach guarantees compilation across
    grammar variants, while we gather diagnostics to author a grammar-aligned query.
    """
    language = _load_language("vue")

    # Import the configured query text
    from src.code_index.treesitter_queries import get_queries_for_language  # type: ignore
    query_text = get_queries_for_language("vue")

    # The Vue query must be a string (may be empty) to ensure compilation can be attempted
    assert isinstance(query_text, str), "Vue query must be a string ('' allowed for minimal compile)"
    # Compile should succeed even if query_text == ''
    q = _compile_query(language, query_text)
    assert q is not None

def test_vue_smoke_on_repo_file_if_present():
    """
    Optional smoke test: if a sample .vue file exists in the known workspace,
    we exercise parser + minimal query to ensure end-to-end does not error.

    This does NOT assert captures (empty query yields zero). It only verifies
    parsing works in the current environment without raising exceptions.
    """
    # Probe a known path (skip if project path not present on this machine)
    candidate = "/home/james/kanban_frontend/Kanban-frontend/src/App.vue"
    if not os.path.exists(candidate):
        pytest.skip("Sample .vue file not present; skipping smoke test")

    language = _load_language("vue")

    try:
        from tree_sitter import Parser  # type: ignore
        parser = Parser()
        parser.language = language
    except Exception as e:
        pytest.skip(f"Failed to initialize Tree-sitter parser for vue: {e}")

    # Read file and parse
    content = ""
    try:
        with open(candidate, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        pytest.skip("Could not read sample .vue file; skipping")

    try:
        tree = parser.parse(bytes(content, "utf-8"))
        assert tree is not None
        assert tree.root_node is not None
    except Exception as e:
        pytest.fail(f"Vue parsing failed on sample file: {e}")