"""O coração assombrado da BBS.

Uma task asyncio que, em intervalos aleatórios, escolhe uma persona e:
  - responde ao post humano mais antigo sem resposta (prioridade), ou
  - cria um post espontâneo sobre um tema de 1986.

Resultado: você posta hoje, reconecta amanhã e a placa "viveu" sem você.
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Optional

from .config import Config
from .llm import LLMClient, LLMError
from .montagens import buscar, by_id
from .personas import PERSONAS, Persona
from .store import Post, Store

log = logging.getLogger("ghostbbs.ghosts")

TOPICS = [
    ("HARDWARE", "uma gambiarra que voce fez no seu TK90X ou CP-500 no fim de semana"),
    ("SOFTWARE", "uma listagem em BASIC ou COBOL que voce esta digitando da revista"),
    ("GERAL", "um boato sobre um micro de 16 bits que dizem que vai furar a reserva de mercado"),
    ("FONE", "uma historia estranha que aconteceu numa ligacao DDD ou num orelhao"),
    ("GERAL", "uma critica ou elogio ao tempo de conexao e ao custo do pulso telefonico"),
    ("HARDWARE", "uma duvida sobre drive de 5 1/4, fita K7 ou o modem da placa"),
    ("BANCADA", "uma montagem barata com CI 555 e protoboard pra fazer em casa"),
    ("BANCADA", "como soldar sem fritar o componente e onde achar peca barata"),
]


class GhostDaemon:
    def __init__(self, cfg: Config, store: Store, llm: LLMClient):
        self.cfg = cfg
        self.store = store
        self.llm = llm
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    # ------------------------------------------------------------------ #
    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="ghost-daemon")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    # ------------------------------------------------------------------ #
    async def _run(self) -> None:
        while not self._stop.is_set():
            delay = random.uniform(self.cfg.ghost_interval_min, self.cfg.ghost_interval_max)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=delay)
                return
            except asyncio.TimeoutError:
                pass
            try:
                await self.tick()
            except Exception:  # noqa: BLE001 - daemon não pode morrer
                log.exception("Erro no tick do daemon fantasma")

    # ------------------------------------------------------------------ #
    async def tick(self) -> Optional[int]:
        """Uma rodada de atividade fantasma. Retorna o id do post criado."""
        pending = self.store.pending_human_post()
        if pending and random.random() < self.cfg.ghost_reply_bias:
            return await self._reply_to(pending)
        return await self._spontaneous_post()

    # ------------------------------------------------------------------ #
    async def _reply_to(self, post: Post) -> Optional[int]:
        persona = self._pick_persona(exclude=post.author)
        prompt = (
            f"No forum {post.board} da BBS, o usuario {post.author} escreveu:\n"
            f"---\n{post.body}\n---\n"
            "Escreva sua resposta a essa mensagem, no seu estilo."
        )
        # se for o professor, ancora a resposta numa montagem do acervo
        if persona.handle == "MESTRE.555":
            m = buscar(post.body)
            if m is not None:
                prompt += (
                    f"\nO leitor casa com a montagem {m.id} do seu acervo "
                    f"({m.base}). Recomende-a pelo nome, citando os componentes "
                    "exatos do acervo."
                )
        body = await self._generate(persona, prompt)
        if body is None:
            return None
        new_id = self.store.add_post(
            post.board, persona.handle, body, is_ghost=True, reply_to=post.id
        )
        self.store.mark_ghost_replied(post.id)
        log.info("%s respondeu ao post #%d em %s", persona.handle, post.id, post.board)
        return new_id

    async def _spontaneous_post(self) -> Optional[int]:
        persona = self._pick_persona()
        board, topic = random.choice(TOPICS)
        prompt = f"Escreva uma mensagem nova para o forum {board} da BBS sobre: {topic}."
        body = await self._generate(persona, prompt)
        if body is None:
            return None
        new_id = self.store.add_post(board, persona.handle, body, is_ghost=True)
        log.info("%s postou espontaneamente em %s", persona.handle, board)
        return new_id

    # ------------------------------------------------------------------ #
    async def _generate(self, persona: Persona, prompt: str) -> Optional[str]:
        try:
            text = await self.llm.chat(
                [
                    {"role": "system", "content": persona.system},
                    {"role": "user", "content": prompt},
                ]
            )
        except LLMError as exc:
            log.warning("LLM indisponível, pulando tick: %s", exc)
            return None
        return _sanitize(text)

    @staticmethod
    def _pick_persona(exclude: str | None = None) -> Persona:
        pool = [p for p in PERSONAS if p.handle != exclude] or PERSONAS
        return random.choice(pool)


def _sanitize(text: str, max_lines: int = 8, width: int = 76) -> str:
    """Garante texto plano, curto, em colunas de BBS."""
    lines: list[str] = []
    for raw in text.replace("\r", "").split("\n"):
        raw = raw.strip()
        if not raw:
            continue
        while len(raw) > width:
            cut = raw.rfind(" ", 0, width)
            cut = cut if cut > 0 else width
            lines.append(raw[:cut])
            raw = raw[cut:].strip()
        lines.append(raw)
        if len(lines) >= max_lines:
            break
    return "\n".join(lines[:max_lines])
