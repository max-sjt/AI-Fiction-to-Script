from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class QwenSettings:
    api_key: str | None = None
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    timeout_seconds: int = 90

    @classmethod
    def from_env(cls) -> "QwenSettings":
        return cls(
            api_key=os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY"),
            base_url=os.getenv("QWEN_BASE_URL", cls.base_url),
            timeout_seconds=int(os.getenv("QWEN_TIMEOUT_SECONDS", "90")),
        )

