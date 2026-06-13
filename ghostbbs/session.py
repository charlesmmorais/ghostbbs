"""Sessão interativa da BBS (independente de transporte).

A classe Session fala com o usuário através de duas corrotinas injetadas
(read_line / write), então o MESMO código serve telnet e serial.
Inclui o throttle de baud para a estética autêntica de 300/1200 bps.
"""
from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable

from .config import Config
from .doorgame import DoorGame
from .ghosts import _sanitize
from .llm import LLMClient, LLMError
from .personas import PERSONAS, persona_by_handle
from .montagens import ACERVO, ficha
from .store import Store

CRLF = "\r\n"

BANNER = r"""
        ________________________________________________________________
       |                                                                |
       |  ##   ##  #####  ######  ######  ######  ##   ##              |
       |  ##   ## ##   ## ##   ##   ##    ##       ## ##    ####   ##  |
       |  ##   ## ##   ## ######    ##    ####      ###    ##  ##  ##  |
       |   ## ##  ##   ## ##  ##    ##    ##       ## ##    ####   ##  |
       |    ###    #####  ##   ##   ##    ######  ##   ##  ##  ##      |
       |                                            8 6     ####       |
       |________________________________________________________________|
"""


class Session:
    def __init__(
        self,
        cfg: Config,
        store: Store,
        llm: LLMClient,
        read_line: Callable[[], Awaitable[str]],
        write_raw: Callable[[bytes], Awaitable[None]],
    ):
        self.cfg = cfg
        self.store = store
        self.llm = llm
        self._read_line = read_line
        self._write_raw = write_raw
        self.handle = "VISITANTE"

    # ------------------------------------------------------ I/O básico #
    async def write(self, text: str) -> None:
        data = text.replace("\n", CRLF).encode("ascii", errors="replace")
        if self.cfg.emulated_baud > 0:
            # 1 caractere = ~10 bits na linha (8N1 + start/stop)
            delay = 10.0 / self.cfg.emulated_baud
            chunk = max(1, int(0.05 / delay)) if delay < 0.05 else 1
            for i in range(0, len(data), chunk):
                await self._write_raw(data[i : i + chunk])
                await asyncio.sleep(delay * min(chunk, len(data) - i))
        else:
            await self._write_raw(data)

    async def writeln(self, text: str = "") -> None:
        await self.write(text + "\n")

    async def prompt(self, label: str) -> str:
        await self.write(label)
        line = await self._read_line()
        return line.strip()

    # ------------------------------------------------------------ fluxo #
    async def run(self) -> None:
        await self.write(BANNER)
        await self.writeln(f"{self.cfg.bbs_name} * {self.cfg.bbs_node_city} * NO AR DESDE 1984")
        await self.writeln(f"CONECTADO A {self.cfg.emulated_baud or 'MAX'} BPS * ANO CORRENTE: {self.cfg.bbs_year}")
        await self.writeln("-" * 64)
        name = await self.prompt("Seu apelido (handle): ")
        if name:
            self.handle = name.upper()[:16]
        await self.writeln(f"\nBem-vindo a bordo, {self.handle}. O SysOp esta de olho.\n")

        while True:
            choice = (await self._menu()).upper()
            if choice == "F":
                await self._boards()
            elif choice == "C":
                await self._chat_sysop()
            elif choice == "D":
                await self._door()
            elif choice == "A":
                await self._acervo()
            elif choice == "Q":
                await self._who()
            elif choice == "G":
                await self.writeln("\nNO CARRIER\n")
                return
            else:
                await self.writeln("Comando desconhecido. Tente de novo.")

    async def _menu(self) -> str:
        await self.writeln(
            "\n=== MENU PRINCIPAL ===========================================\n"
            " [F] Foruns de mensagens     [C] Chat com o SysOp\n"
            " [D] Door game: O CPD ABANDONADO\n"
            " [A] Acervo de montagens do MESTRE.555\n"
            " [Q] Quem esta na placa      [G] Desligar (goodbye)\n"
            "=============================================================="
        )
        return await self.prompt("Sua escolha: ")

    # ------------------------------------------------------------ áreas #
    async def _who(self) -> None:
        await self.writeln("\nUSUARIOS DA PLACA (ultimas 24h):")
        await self.writeln(f"  {self.handle:<14} <- VOCE (no node 1)")
        for p in PERSONAS:
            await self.writeln(f"  {p.handle:<14} {p.bio}")

    async def _boards(self) -> None:
        while True:
            await self.writeln("\n--- FORUNS -------------------------------------------------")
            for name, descr, count in self.store.boards():
                await self.writeln(f"  {name:<10} ({count:>3} msgs)  {descr}")
            sel = (await self.prompt("Forum (ou ENTER p/ voltar): ")).upper()
            if not sel:
                return
            names = [b[0] for b in self.store.boards()]
            if sel not in names:
                await self.writeln("Forum inexistente.")
                continue
            await self._board(sel)

    async def _board(self, board: str) -> None:
        while True:
            posts = self.store.posts(board, limit=15)
            await self.writeln(f"\n*** {board} *** ({len(posts)} mensagens recentes)")
            if not posts:
                await self.writeln("  (vazio... por enquanto)")
            for p in posts:
                ts = time.strftime("%d/%m %H:%M", time.localtime(p.ts))
                ref = f" re:#{p.reply_to}" if p.reply_to else ""
                await self.writeln(f"\n#{p.id} de {p.author} em {ts}{ref}")
                for line in p.body.split("\n"):
                    await self.writeln(f"  {line}")
            cmd = (await self.prompt("\n[P]ostar  [ENTER] voltar: ")).upper()
            if cmd != "P":
                return
            await self.writeln("Digite sua mensagem. Linha vazia encerra.")
            lines: list[str] = []
            while True:
                line = await self._read_line()
                if not line.strip():
                    break
                lines.append(line.rstrip()[:76])
                if len(lines) >= 10:
                    break
            if lines:
                pid = self.store.add_post(board, self.handle, "\n".join(lines))
                await self.writeln(
                    f"Mensagem #{pid} gravada. Os outros usuarios da placa\n"
                    "costumam responder em algumas horas. Volte depois!"
                )

    async def _chat_sysop(self) -> None:
        sysop = persona_by_handle("VECTOR")
        assert sysop is not None
        await self.writeln(
            "\n*** PAGINANDO O SYSOP... ele atendeu! ***\n"
            "(digite /SAIR para encerrar o chat)\n"
        )
        history: list[dict[str, str]] = []
        while True:
            text = await self.prompt(f"{self.handle}> ")
            if text.upper() in ("/SAIR", "/QUIT", "/EXIT"):
                await self.writeln("VECTOR> Falou. Nao derruba a portadora saindo, hein.")
                return
            if not text:
                continue
            history.append({"role": "user", "content": f"{self.handle} diz: {text}"})
            try:
                reply = await self.llm.chat(
                    [{"role": "system", "content": sysop.system}, *history[-8:]]
                )
            except LLMError:
                await self.writeln("*** LINHA RUIDOSA *** o SysOp nao ouviu. Repita.")
                history.pop()
                continue
            reply = _sanitize(reply)
            history.append({"role": "assistant", "content": reply})
            for line in reply.split("\n"):
                await self.writeln(f"VECTOR> {line}")

    async def _acervo(self) -> None:
        while True:
            await self.writeln(
                "\n+--- ACERVO DE MONTAGENS DO MESTRE.555 -----------------------+\n"
                '| "Monte voce mesmo, rapaz! Caixa-preta nao ensina ninguem." |\n'
                "+------------------------------------------------------------+"
            )
            for i, m in enumerate(ACERVO, 1):
                risco = " (!)" if m.aviso and "MORTE" in m.aviso else ""
                await self.writeln(
                    f"  [{i}] {m.id:<13} {m.dificuldade:<13} {m.base[:28]}{risco}"
                )
            await self.writeln("  (!) = mexe na tensao da rede, cuidado")
            sel = (await self.prompt("\nNumero da ficha (ou ENTER p/ voltar): ")).strip()
            if not sel:
                return
            if not sel.isdigit() or not (1 <= int(sel) <= len(ACERVO)):
                await self.writeln("Ficha inexistente, meu caro.")
                continue
            await self.writeln("")
            await self.writeln(ficha(ACERVO[int(sel) - 1]))

    async def _door(self) -> None:
        game = DoorGame(self.cfg, self.llm)
        await self.writeln("\n>>> ABRINDO DOOR: O CPD ABANDONADO <<<\n")
        await self.writeln(await game.start())
        while True:
            cmd = await self.prompt("\n> ")
            if cmd.upper() in ("SAIR", "QUIT", "EXIT"):
                await self.writeln("\n>>> Voce desliga o terminal e volta para a BBS. <<<")
                return
            if not cmd:
                continue
            await self.writeln("")
            await self.writeln(await game.command(cmd))
