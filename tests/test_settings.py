from __future__ import annotations

from ai_fiction_to_script.settings import DEFAULT_QWEN_BASE_URL, DEFAULT_QWEN_TIMEOUT_SECONDS, QwenSettings


def test_qwen_settings_from_env_uses_string_defaults(monkeypatch) -> None:
    monkeypatch.delenv("QWEN_BASE_URL", raising=False)
    monkeypatch.delenv("QWEN_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)

    settings = QwenSettings.from_env(api_key_override="demo-key")

    assert settings.api_key == "demo-key"
    assert settings.base_url == DEFAULT_QWEN_BASE_URL
    assert settings.timeout_seconds == DEFAULT_QWEN_TIMEOUT_SECONDS
    assert settings.base_url.rstrip("/") == DEFAULT_QWEN_BASE_URL.rstrip("/")
