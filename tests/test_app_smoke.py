"""
Smoke test: the Streamlit app renders its landing page without errors.
Runs in CI (where Streamlit is installed); skipped elsewhere.
"""

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402


def test_landing_page_renders():
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception
    assert any("YouTube" in md.value for md in at.markdown)
    assert at.sidebar.selectbox  # model picker present
