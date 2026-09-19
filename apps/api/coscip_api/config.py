from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> Path:
    # Pasta privada, não sincronizada: dados locais do app no perfil Windows (plano §13).
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "MotorCoscip"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COSCIP_", extra="ignore")

    data_dir: Path = _default_data_dir()
    host: str = "127.0.0.1"  # nunca 0.0.0.0: rede exige autenticação multiusuário
    port: int = 0  # escolhida pelo launcher
    launch_token: str | None = None  # uso único, entregue pelo launcher
    dev_origin: str | None = None  # ex.: http://localhost:5173 no desenvolvimento

    # Limites propostos (plano §2), a ajustar na POC.
    max_upload_bytes: int = 50 * 1024 * 1024
    max_expanded_entities: int = 2_000_000
    worker_memory_mb: int = 4096
    worker_timeout_s: int = 30 * 60
    disk_reserve_factor: int = 5

    # IA: desligada por padrão; tetos propostos em USD.
    ai_enabled: bool = False
    ai_per_analysis_usd: str = "0.25"
    ai_per_month_usd: str = "5.00"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{(self.data_dir / 'database' / 'app.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
