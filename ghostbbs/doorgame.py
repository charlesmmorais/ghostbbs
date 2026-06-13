"""Door game: "O CPD ABANDONADO" — aventura de texto conduzida pelo LLM.

Mantém o histórico da sessão (o AX630C tem contexto curto; limitamos o
histórico às últimas N trocas para caber no modelo de 0.5B).
"""
from __future__ import annotations

from typing import Dict, List

from .config import Config
from .llm import LLMClient, LLMError

SYSTEM = (
    "Você é o mestre de uma AVENTURA de texto estilo anos 80 chamada "
    "'O CPD ABANDONADO'. Ambientação: o centro de processamento de dados de "
    "uma estatal brasileira, abandonado em 1986. Mainframes desligados, fitas "
    "magnéticas, leitoras de cartao perfurado, um TK90X esquecido numa mesa, "
    "cartazes da reserva de mercado, luzes de emergencia ambar. O jogador "
    "explora digitando comandos curtos (IR NORTE, PEGAR FITA, LER TERMINAL, "
    "LIGAR MICRO...). Responda SEMPRE em português do Brasil, texto puro sem "
    "acentos, no máximo 8 linhas de 70 colunas, terminando com uma pergunta ou "
    "as saídas disponíveis. Seja atmosférico, levemente sinistro, com sabor "
    "brasileiro de época, e nunca quebre o personagem."
)

OPENING_CMD = "Comece a aventura descrevendo a entrada do CPD."
MAX_TURNS_KEPT = 6  # pares user/assistant mantidos no contexto


class DoorGame:
    def __init__(self, cfg: Config, llm: LLMClient):
        self.cfg = cfg
        self.llm = llm
        self.history: List[Dict[str, str]] = []

    async def start(self) -> str:
        return await self._turn(OPENING_CMD)

    async def command(self, text: str) -> str:
        return await self._turn(text.strip()[:120])

    async def _turn(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})
        # janela deslizante de contexto
        window = self.history[-(MAX_TURNS_KEPT * 2):]
        messages = [{"role": "system", "content": SYSTEM}, *window]
        try:
            reply = await self.llm.chat(messages)
        except LLMError:
            reply = (
                "*** RUIDO NA LINHA *** O mestre do jogo nao respondeu.\n"
                "Tente novamente ou digite SAIR."
            )
            self.history.pop()
            return reply
        self.history.append({"role": "assistant", "content": reply})
        return reply
