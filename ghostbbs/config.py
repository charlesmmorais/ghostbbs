"""Configuração central do GhostBBS.

Tudo pode ser sobrescrito por variáveis de ambiente, o que facilita
rodar no Module LLM (produção) e no desenvolvimento (mock).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass
class Config:
    # --- Rede ---
    telnet_host: str = field(default_factory=lambda: _env("GHOSTBBS_HOST", "0.0.0.0"))
    telnet_port: int = field(default_factory=lambda: int(_env("GHOSTBBS_PORT", "2323")))

    # --- Serial (opcional: terminal de época / Altair) ---
    serial_device: str = field(default_factory=lambda: _env("GHOSTBBS_SERIAL", ""))
    serial_baud: int = field(default_factory=lambda: int(_env("GHOSTBBS_SERIAL_BAUD", "300")))

    # --- LLM (plugin openai-api do StackFlow no Module LLM) ---
    llm_base_url: str = field(
        default_factory=lambda: _env("GHOSTBBS_LLM_URL", "http://127.0.0.1:8000/v1")
    )
    llm_model: str = field(default_factory=lambda: _env("GHOSTBBS_LLM_MODEL", "qwen2.5-0.5B-prefill-20e"))
    llm_api_key: str = field(default_factory=lambda: _env("GHOSTBBS_LLM_KEY", "no-key-needed"))
    llm_max_tokens: int = field(default_factory=lambda: int(_env("GHOSTBBS_LLM_MAXTOK", "256")))
    llm_timeout_s: float = field(default_factory=lambda: float(_env("GHOSTBBS_LLM_TIMEOUT", "120")))
    # mock=1 -> respostas determinísticas, sem hardware (CI / testes)
    llm_mock: bool = field(default_factory=lambda: _env("GHOSTBBS_MOCK", "0") == "1")

    # --- Simulação de baud rate na saída (autenticidade!) ---
    # 0 = sem limite; 300 ou 1200 recomendados para a experiência completa
    emulated_baud: int = field(default_factory=lambda: int(_env("GHOSTBBS_EMU_BAUD", "1200")))

    # --- Persistência ---
    db_path: str = field(default_factory=lambda: _env("GHOSTBBS_DB", "ghostbbs.sqlite3"))

    # --- Daemon dos fantasmas ---
    # intervalo entre "atividades" dos usuários fantasmas (segundos)
    ghost_interval_min: float = field(default_factory=lambda: float(_env("GHOSTBBS_GHOST_MIN", "600")))
    ghost_interval_max: float = field(default_factory=lambda: float(_env("GHOSTBBS_GHOST_MAX", "3600")))
    # probabilidade de responder a um post humano pendente em vez de criar post novo
    ghost_reply_bias: float = field(default_factory=lambda: float(_env("GHOSTBBS_REPLY_BIAS", "0.8")))

    # --- Identidade da BBS ---
    bbs_name: str = field(default_factory=lambda: _env("GHOSTBBS_NAME", "VORTEX-86 BBS"))
    bbs_year: str = field(default_factory=lambda: _env("GHOSTBBS_YEAR", "1986"))
    bbs_node_city: str = field(default_factory=lambda: _env("GHOSTBBS_CITY", "Brasilia/DF"))
