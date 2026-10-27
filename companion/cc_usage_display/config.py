from __future__ import annotations

import json
import math
import os
import secrets
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


DEFAULT_USD_TO_CNY = 6.684864


def default_db_path() -> Path:
    return Path.home() / ".cc-switch" / "cc-switch.db"


def default_config_path() -> Path:
    return Path.home() / ".cc-usage-display" / "config.json"


def default_cc_switch_exe() -> Optional[str]:
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            return None
        candidate = Path(local_app_data) / "Programs" / "CC Switch" / "cc-switch.exe"
        return str(candidate) if candidate.exists() else None

    if sys.platform == "darwin":
        for candidate in (
            Path("/Applications/CC Switch.app"),
            Path.home() / "Applications" / "CC Switch.app",
        ):
            if candidate.exists():
                return str(candidate)

    return None


@dataclass
class Config:
    db_path: str
    host: str
    port: int
    token: str
    refresh_seconds: int
    cc_switch_exe: Optional[str]
    usd_to_cny: float


def _read_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        raise SystemExit(f"Cannot read config {path}: {error}") from error


def _write_file(path: Path, values: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def load_config(
    config_path: Optional[str] = None,
    db_path: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    token: Optional[str] = None,
) -> Config:
    path = Path(config_path).expanduser() if config_path else default_config_path()
    values = _read_file(path)

    values.setdefault("db_path", str(default_db_path()))
    values.setdefault("host", "0.0.0.0")
    values.setdefault("port", 8787)
    values.setdefault("refresh_seconds", 15)
    values.setdefault("cc_switch_exe", default_cc_switch_exe())
    values.setdefault("usd_to_cny", DEFAULT_USD_TO_CNY)

    env_db = os.environ.get("CC_SWITCH_DB")
    env_token = os.environ.get("CC_USAGE_TOKEN")
    if env_db:
        values["db_path"] = env_db
    if env_token:
        values["token"] = env_token
    if db_path:
        values["db_path"] = db_path
    if host:
        values["host"] = host
    if port:
        values["port"] = port
    if token:
        values["token"] = token

    try:
        usd_to_cny = float(values["usd_to_cny"])
    except (TypeError, ValueError):
        usd_to_cny = DEFAULT_USD_TO_CNY
    if not math.isfinite(usd_to_cny) or usd_to_cny <= 0:
        usd_to_cny = DEFAULT_USD_TO_CNY
    values["usd_to_cny"] = usd_to_cny

    if not values.get("token"):
        values["token"] = secrets.token_urlsafe(18)

    _write_file(path, values)
    return Config(**values)


def public_config(config: Config) -> dict:
    values = asdict(config)
    values["token"] = "***"
    return values
