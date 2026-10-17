import importlib

import pytest

import config

CONTENT = "GEMINI_API_KEY=abc123\nGEMINI_MODEL=gemini-3.5-flash\n"


@pytest.mark.parametrize(
    "raw",
    [
        CONTENT.encode("utf-8"),
        b"\xef\xbb\xbf" + CONTENT.encode("utf-8"),          # UTF-8 with BOM (Set-Content -Encoding utf8)
        CONTENT.encode("utf-16"),                            # UTF-16 LE with BOM (echo > .env)
        CONTENT.replace("\n", "\r\n").encode("utf-8"),       # Windows line endings
        b'GEMINI_API_KEY = "abc123"\n',       # spaces + quotes
    ],
)
def test_env_file_variants_are_read(tmp_path, monkeypatch, raw):
    env = tmp_path / ".env"
    env.write_bytes(raw)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    config._load_env_file(env)
    import os

    assert os.environ["GEMINI_API_KEY"] == "abc123"


def test_empty_real_env_var_is_filled_but_real_value_wins(tmp_path, monkeypatch):
    import os

    env = tmp_path / ".env"
    env.write_text(CONTENT, encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    config._load_env_file(env)
    assert os.environ["GEMINI_API_KEY"] == "abc123"

    monkeypatch.setenv("GEMINI_API_KEY", "from-platform")
    config._load_env_file(env)
    assert os.environ["GEMINI_API_KEY"] == "from-platform"


def test_settings_pick_up_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "xyz")
    assert importlib.reload(config).settings.gemini_api_key == "xyz"
