"""Cliente do LLM local.

No Module LLM (AX630C), o plugin `llm-openai-api` do StackFlow expõe uma API
compatível com OpenAI em http://127.0.0.1:8000/v1. Este cliente usa apenas a
stdlib (urllib) para não ter dependências externas no módulo.

Em modo mock (GHOSTBBS_MOCK=1), gera respostas determinísticas — usado nos
testes automatizados e para desenvolver sem o hardware.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import urllib.request
from typing import Dict, List

from .config import Config

Message = Dict[str, str]  # {"role": ..., "content": ...}


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    # ------------------------------------------------------------------ #
    async def chat(self, messages: List[Message], max_tokens: int | None = None) -> str:
        """Envia uma conversa e retorna o texto da resposta."""
        if self.cfg.llm_mock:
            return self._mock_reply(messages)
        return await asyncio.to_thread(self._chat_blocking, messages, max_tokens)

    # ------------------------------------------------------------------ #
    def _chat_blocking(self, messages: List[Message], max_tokens: int | None) -> str:
        payload = {
            "model": self.cfg.llm_model,
            "messages": messages,
            "max_tokens": max_tokens or self.cfg.llm_max_tokens,
            "stream": False,
        }
        req = urllib.request.Request(
            self.cfg.llm_base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.cfg.llm_api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.llm_timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - queremos degradar com elegância
            raise LLMError(f"Falha ao consultar o LLM local: {exc}") from exc

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Resposta inesperada do LLM: {data!r}") from exc

    # ------------------------------------------------------------------ #
    def _mock_reply(self, messages: List[Message]) -> str:
        """Resposta determinística baseada no hash da conversa.

        Suficiente para testar fluxo, persistência e UI sem hardware.
        """
        last = messages[-1]["content"] if messages else ""
        h = hashlib.sha1(last.encode("utf-8")).hexdigest()[:6]
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        if "AVENTURA" in system.upper():
            return (
                "Voce esta numa sala de maquinas iluminada por LEDs ambar. "
                f"Um terminal pisca o codigo {h}. Saidas: NORTE, LESTE.\n"
                "O que voce faz?"
            )
        return f"[mock:{h}] Entendido. Mensagem recebida na VORTEX-86."
