from __future__ import annotations
import yaml
from pathlib import Path
from typing import Optional


class Config:
    def __init__(self, path: Optional[str] = None):
        # Load config.yaml from project root by default
        if path is not None:
            config_path = Path(path)
        else:
            config_path = Path(__file__).parent.parent / "config.yaml"
        data = yaml.safe_load(config_path.read_text()) or {}

        prompts = data.get("prompts", {})
        self.user_message_base: str = prompts.get("user_message_base", "")
        self.system_event: str = prompts.get("system_event", "")

        self.mcp = data.get("mcp", {})

# Singleton config instance
def default_config(path: Optional[str] = None) -> Config:
    return Config(path)

config = default_config()
