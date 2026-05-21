"""Rule base class, Result types, and registry system."""
from __future__ import annotations
import importlib
import inspect
import pkgutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


class Status(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class Result:
    status: Status
    message: str
    details: str = ""
    time_range: tuple[float, float] | None = None
    value: float | None = None
    threshold: float | None = None


class Rule(ABC):
    """Base class for all telemetry rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def check(self, df: pd.DataFrame, config: dict[str, Any]) -> list[Result]:
        """Run this rule against the telemetry data.

        Args:
            df: Preprocessed DataFrame (numeric, fillna(0), downsampled)
            config: Thresholds and settings from rules_config.yaml
        """
        pass

    @property
    def supports_multi(self) -> bool:
        """Can this rule compare across multiple files?"""
        return False


# Global registry of Rule subclasses
_RULE_REGISTRY: dict[str, type[Rule]] = {}


def register_rule(cls: type[Rule]) -> type[Rule]:
    """Decorator to register a Rule subclass."""
    _RULE_REGISTRY[cls.__name__] = cls
    return cls


def get_registry() -> dict[str, type[Rule]]:
    return dict(_RULE_REGISTRY)


def load_all_rules() -> None:
    """Auto-discover and import all rule modules from rules_impl/."""
    rules_pkg = importlib.import_module("app.services.rules_engine.rules_impl")
    pkg_path = Path(rules_pkg.__path__[0])
    for module_info in pkgutil.iter_modules([str(pkg_path)]):
        if module_info.name.startswith("_"):
            continue
        importlib.import_module(f"app.services.rules_engine.rules_impl.{module_info.name}")


def load_config() -> dict[str, Any]:
    """Load rule thresholds from rules_config.yaml."""
    config_path = Path(__file__).resolve().parent.parent.parent / "rules_config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_channel(df: pd.DataFrame, channel_name: str) -> pd.Series | None:
    """Safely get a channel by name, returning None if not present."""
    if channel_name in df.columns:
        return df[channel_name]
    # Try partial match (case-insensitive)
    for col in df.columns:
        if channel_name.lower() in col.lower():
            return df[col]
    return None
