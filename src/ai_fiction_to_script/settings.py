from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_QWEN_TIMEOUT_SECONDS = 150


@dataclass(slots=True)
class QwenSettings:
    api_key: str | None = None
    base_url: str = DEFAULT_QWEN_BASE_URL
    timeout_seconds: int = DEFAULT_QWEN_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls, api_key_override: str | None = None) -> "QwenSettings":
        return cls(
            api_key=api_key_override or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY"),
            base_url=os.getenv("QWEN_BASE_URL") or DEFAULT_QWEN_BASE_URL,
            timeout_seconds=int(os.getenv("QWEN_TIMEOUT_SECONDS", str(DEFAULT_QWEN_TIMEOUT_SECONDS))),
        )
