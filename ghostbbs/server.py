"""Transportes da GhostBBS: telnet (asyncio) e serial (opcional).

Telnet: implementação minimalista — filtramos sequências IAC do cliente e
servimos texto puro. Funciona com `telnet`, PuTTY, SyncTERM, netcat...

Serial: se GHOSTBBS_SERIAL apontar para um device (ex.: /dev/ttyS1 no
Module LLM via FPC-8P/Mate), abrimos com pyserial-asyncio se disponível;
o baud REAL da porta + o throttle emulado dão a experiência 1986 completa
num VT100 ou num Altair com SIO-2.
"""
from __future__ import annotations

import asyncio
import logging

from .config import Config
from .ghosts import GhostDaemon
from .llm import LLMClient
from .session import Session
from .store import Store

log = logging.getLogger("ghostbbs.server")

IAC = 255  # telnet Interpret As Command


class TelnetLineReader:
    """Lê linhas de um StreamReader filtrando negociação telnet básica."""

    def __init__(self, reader: asyncio.StreamReader):
        self.reader = reader

    async def read_line(self) -> str:
        buf = bytearray()
        while True:
            b = await self.reader.read(1)
            if not b:
                raise ConnectionResetError("cliente desconectou")
            x = b[0]
            if x == IAC:  # consome comando telnet (IAC + cmd [+ opt])
                cmd = await self.reader.read(1)
                if cmd and cmd[0] in (251, 252, 253, 254):  # WILL/WONT/DO/DONT
                    await self.reader.read(1)
                continue
            if x in (10,):  # LF encerra a linha
                break
            if x in (13, 0):  # CR/NUL ignorados
                continue
            if x in (8, 127):  # backspace
                if buf:
                    buf.pop()
                continue
            if 32 <= x < 127:
                buf.append(x)
        return buf.decode("ascii", errors="replace")


class GhostBBSServer:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.store = Store(cfg.db_path)
        self.llm = LLMClient(cfg)
        self.ghosts = GhostDaemon(cfg, self.store, self.llm)
        self._server: asyncio.AbstractServer | None = None

    # ------------------------------------------------------------------ #
    async def start(self) -> None:
        self.ghosts.start()
        self._server = await asyncio.start_server(
            self._handle_client, self.cfg.telnet_host, self.cfg.telnet_port
        )
        addrs = ", ".join(str(s.getsockname()) for s in self._server.sockets)
        log.info("GhostBBS no ar em %s (telnet)", addrs)
        if self.cfg.serial_device:
            asyncio.create_task(self._serial_loop(), name="serial-loop")

    async def stop(self) -> None:
        await self.ghosts.stop()
        if self._server:
            self._server.close()
            try:
                # wait_closed() pode bloquear se houver conexões ainda drenando;
                # damos um tempo razoável e seguimos em frente no encerramento.
                await asyncio.wait_for(self._server.wait_closed(), timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        self.store.close()

    @property
    def port(self) -> int:
        assert self._server is not None
        return self._server.sockets[0].getsockname()[1]

    # ------------------------------------------------------------------ #
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        log.info("Conexao de %s", peer)
        line_reader = TelnetLineReader(reader)

        async def write_raw(data: bytes) -> None:
            writer.write(data)
            await writer.drain()

        session = Session(self.cfg, self.store, self.llm, line_reader.read_line, write_raw)
        try:
            await session.run()
        except (ConnectionResetError, asyncio.IncompleteReadError):
            log.info("%s caiu a portadora", peer)
        except Exception:  # noqa: BLE001
            log.exception("Erro na sessao de %s", peer)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------ #
    async def _serial_loop(self) -> None:
        try:
            import serial_asyncio  # type: ignore
        except ImportError:
            log.error(
                "GHOSTBBS_SERIAL definido mas pyserial-asyncio nao instalado: "
                "pip install pyserial-asyncio"
            )
            return
        while True:
            try:
                reader, writer = await serial_asyncio.open_serial_connection(
                    url=self.cfg.serial_device, baudrate=self.cfg.serial_baud
                )
                log.info("Porta serial %s aberta a %d bps", self.cfg.serial_device, self.cfg.serial_baud)
                line_reader = TelnetLineReader(reader)  # filtro IAC é inócuo na serial

                async def write_raw(data: bytes) -> None:
                    writer.write(data)
                    await writer.drain()

                session = Session(self.cfg, self.store, self.llm, line_reader.read_line, write_raw)
                await session.run()
            except Exception:  # noqa: BLE001
                log.exception("Sessao serial encerrada; reabrindo em 3s")
                await asyncio.sleep(3)


# ---------------------------------------------------------------------- #
async def amain() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    cfg = Config()
    server = GhostBBSServer(cfg)
    await server.start()
    try:
        await asyncio.Event().wait()  # roda até SIGINT/SIGTERM
    finally:
        await server.stop()


def main() -> None:
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
