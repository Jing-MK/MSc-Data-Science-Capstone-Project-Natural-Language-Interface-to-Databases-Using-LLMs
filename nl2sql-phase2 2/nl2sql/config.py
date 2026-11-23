"""Configuration loader.

Loads settings from ``config.local.yaml`` (git-ignored) and lets the
environment variable ``DASHSCOPE_API_KEY`` override the stored key, so a
secret never has to live in the repository.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class LLMConfig:
    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen-plus"
    enable_thinking: bool = False
    temperature: float = 0.0
    timeout_seconds: int = 30


@dataclass
class BirdConfig:
    db_root: str = ""


@dataclass
class FrameworkConfig:
    max_rounds: int = 4
    use_llm_propose: bool = True
    busy_timeout_ms: int = 5000


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    bird: BirdConfig = field(default_factory=BirdConfig)
    framework: FrameworkConfig = field(default_factory=FrameworkConfig)

    def db_path(self, db_id: str) -> str:
        """Return the .sqlite path for a BIRD database id."""
        return str(Path(self.bird.db_root) / db_id / f"{db_id}.sqlite")


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config(path: Optional[str] = None) -> Config:
    """Load configuration.

    Order of precedence for the LLM key:
      1. ``DASHSCOPE_API_KEY`` environment variable
      2. ``api_key`` in config.local.yaml
    """
    root = _project_root()
    if path is None:
        # Prefer the local (git-ignored) config; fall back to the example.
        local = root / "config.local.yaml"
        path = str(local) if local.exists() else str(root / "config.example.yaml")

    data = {}
    p = Path(path)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    cfg = Config()
    if "llm" in data:
        cfg.llm = LLMConfig(**{**cfg.llm.__dict__, **data["llm"]})
    if "bird" in data:
        cfg.bird = BirdConfig(**{**cfg.bird.__dict__, **data["bird"]})
    if "framework" in data:
        cfg.framework = FrameworkConfig(**{**cfg.framework.__dict__, **data["framework"]})

    # Environment variable overrides the stored key.
    env_key = os.environ.get("DASHSCOPE_API_KEY")
    if env_key:
        cfg.llm.api_key = env_key

    return cfg
