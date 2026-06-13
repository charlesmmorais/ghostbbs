#!/usr/bin/env python3
"""Demo automatizada do GhostBBS — sobe a placa em modo mock, conecta um
cliente telnet simulado e percorre login, fórum, post, resposta fantasma e
door game. Útil para ver tudo funcionando sem hardware nem telnet manual.

    python tools/demo.py
"""
from __future__ import annotations

import asyncio
import os
import sys

os.environ.setdefault("GHOSTBBS_MOCK", "1")
os.environ.setdefault("GHOSTBBS_EMU_BAUD", "0")
os.environ.setdefault("GHOSTBBS_GHOST_MIN", "1")
os.environ.setdefault("GHOSTBBS_GHOST_MAX", "2")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ghostbbs.config import Config  # noqa: E402
from ghostbbs.server import GhostBBSServer  # noqa: E402


async def main() -> None:
    cfg = Config()
    cfg.db_path = "/tmp/ghostbbs_demo.sqlite3"
    if os.path.exists(cfg.db_path):
        os.remove(cfg.db_path)
    cfg.telnet_port = 0
    cfg.telnet_host = "127.0.0.1"
    cfg.emulated_baud = 0
    cfg.llm_mock = True

    server = GhostBBSServer(cfg)
    await server.start()
    reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
    buf = b""

    async def until(tok: bytes) -> bytes:
        nonlocal buf
        async with asyncio.timeout(8):
            while tok not in buf:
                chunk = await reader.read(1024)
                if not chunk:
                    break
                buf += chunk
        i = buf.index(tok) + len(tok)
        out, buf = buf[:i], buf[i:]
        sys.stdout.write(out.decode("ascii", "replace"))
        sys.stdout.flush()
        return out

    def send(data: bytes) -> None:
        sys.stdout.write(data.decode() )
        writer.write(data)

    await until(b"handle): ");   send(b"CHARLES\r\n")
    await until(b"Sua escolha: "); send(b"F\r\n")
    await until(b"voltar): ");   send(b"HARDWARE\r\n")
    await until(b"voltar: ");    send(b"P\r\n")
    await until(b"encerra.")
    send(b"Alguem ai ainda usa drive de 5 1/4?\r\n\r\n")
    await until(b"gravada")
    await until(b"voltar: ");    send(b"\r\n")
    await until(b"voltar): ");   send(b"\r\n")
    await until(b"Sua escolha: ")

    print("\n\n--- (esperando um fantasma responder...) ---")
    await server.ghosts.tick()  # força um tick imediato
    send(b"F\r\n")
    await until(b"voltar): ");   send(b"HARDWARE\r\n")
    await until(b"voltar: ");    send(b"\r\n")
    await until(b"voltar): ");   send(b"\r\n")
    await until(b"Sua escolha: ")

    print("\n\n--- (abrindo o door game) ---")
    send(b"D\r\n")
    await until(b"> ")
    send(b"IR NORTE\r\n")
    await until(b"> ")
    send(b"SAIR\r\n")
    await until(b"Sua escolha: "); send(b"G\r\n")
    await until(b"NO CARRIER")

    writer.close()
    try:
        await asyncio.wait_for(writer.wait_closed(), timeout=2)
    except Exception:
        pass
    await server.stop()
    print("\n\n=== demo concluida ===")


if __name__ == "__main__":
    asyncio.run(main())
