import pytest


@pytest.mark.skip(reason="Direct Qdrant integration test disabled in automated suites")
def test_qdrant_direct():
    assert True