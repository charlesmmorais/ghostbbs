"""Testes do GhostBBS — rodam 100% offline com o LLM em modo mock."""
from __future__ import annotations

import asyncio
import os

import pytest

os.environ["GHOSTBBS_MOCK"] = "1"
os.environ["GHOSTBBS_EMU_BAUD"] = "0"  # sem throttle nos testes

from ghostbbs.config import Config  # noqa: E402
from ghostbbs.doorgame import DoorGame  # noqa: E402
from ghostbbs.ghosts import GhostDaemon, _sanitize  # noqa: E402
from ghostbbs.llm import LLMClient  # noqa: E402
from ghostbbs.server import GhostBBSServer  # noqa: E402
from ghostbbs.store import Store  # noqa: E402


def make_cfg(tmp_path, **kw) -> Config:
    cfg = Config()
    cfg.db_path = str(tmp_path / "test.sqlite3")
    cfg.telnet_host = "127.0.0.1"
    cfg.telnet_port = 0  # porta efêmera
    cfg.emulated_baud = 0
    cfg.llm_mock = True
    for k, v in kw.items():
        setattr(cfg, k, v)
    return cfg


# ---------------------------------------------------------------- store #
def test_store_boards_and_posts(tmp_path):
    s = Store(str(tmp_path / "db.sqlite3"))
    boards = s.boards()
    assert {b[0] for b in boards} >= {"GERAL", "HARDWARE", "SOFTWARE", "FONE"}

    pid = s.add_post("GERAL", "CHARLES", "Ola placa! Alguem ai tem um CP-500?")
    posts = s.posts("GERAL")
    assert posts[-1].id == pid
    assert posts[-1].author == "CHARLES"
    assert not posts[-1].is_ghost

    pending = s.pending_human_post()
    assert pending is not None and pending.id == pid
    s.mark_ghost_replied(pid)
    assert s.pending_human_post() is None
    s.close()


# ------------------------------------------------------------------ llm #
@pytest.mark.asyncio
async def test_llm_mock_deterministic(tmp_path):
    llm = LLMClient(make_cfg(tmp_path))
    msgs = [{"role": "user", "content": "teste"}]
    a = await llm.chat(msgs)
    b = await llm.chat(msgs)
    assert a == b and a.startswith("[mock:")


def test_sanitize_wraps_and_limits():
    long = "palavra " * 60
    out = _sanitize(long, max_lines=4, width=40)
    lines = out.split("\n")
    assert len(lines) <= 4
    assert all(len(line) <= 40 for line in lines)


# --------------------------------------------------------------- ghosts #
@pytest.mark.asyncio
async def test_ghost_replies_to_human_post(tmp_path):
    cfg = make_cfg(tmp_path, ghost_reply_bias=1.0)
    store = Store(cfg.db_path)
    llm = LLMClient(cfg)
    daemon = GhostDaemon(cfg, store, llm)

    pid = store.add_post("HARDWARE", "CHARLES", "Meu drive de 5 1/4 nao le mais nada.")
    new_id = await daemon.tick()
    assert new_id is not None

    reply = store.get_post(new_id)
    assert reply is not None
    assert reply.is_ghost
    assert reply.reply_to == pid
    assert reply.board == "HARDWARE"
    assert store.pending_human_post() is None  # marcado como respondido
    store.close()


@pytest.mark.asyncio
async def test_ghost_spontaneous_post(tmp_path):
    cfg = make_cfg(tmp_path)
    store = Store(cfg.db_path)
    daemon = GhostDaemon(cfg, store, LLMClient(cfg))
    new_id = await daemon.tick()  # sem post humano pendente -> espontâneo
    post = store.get_post(new_id)
    assert post is not None and post.is_ghost and post.reply_to is None
    store.close()


# ----------------------------------------------------- personas / boards #
def test_mestre555_persona_is_fictional():
    from ghostbbs.personas import persona_by_handle

    prof = persona_by_handle("MESTRE.555")
    assert prof is not None
    # tom e domínio do professor de eletrônica
    assert "555" in prof.system
    assert "ferro de solda" in prof.system.lower()
    # salvaguarda: o personagem é explicitamente fictício
    assert "FICTICIO" in prof.system.upper()


def test_bancada_board_exists(tmp_path):
    s = Store(str(tmp_path / "b.sqlite3"))
    names = {b[0] for b in s.boards()}
    assert "BANCADA" in names
    s.close()


@pytest.mark.asyncio
async def test_mestre555_can_reply(tmp_path):
    cfg = make_cfg(tmp_path, ghost_reply_bias=1.0)
    store = Store(cfg.db_path)
    daemon = GhostDaemon(cfg, store, LLMClient(cfg))
    pid = store.add_post("BANCADA", "CHARLES", "Como faco um pisca-pisca simples?")
    # força a escolha do professor
    from ghostbbs.personas import persona_by_handle

    daemon._pick_persona = staticmethod(lambda exclude=None: persona_by_handle("MESTRE.555"))  # type: ignore
    new_id = await daemon.tick()
    reply = store.get_post(new_id)
    assert reply is not None and reply.author == "MESTRE.555"
    assert reply.reply_to == pid
    store.close()


# --------------------------------------------------------- acervo 555 #
def test_acervo_integrity():
    from ghostbbs.montagens import ACERVO

    ids = {m.id for m in ACERVO}
    # as tres montagens pedidas existem
    assert {"PISCA-PISCA", "SIRENE", "DIMMER"} <= ids
    # cada montagem esta bem-formada
    for m in ACERVO:
        assert m.nome and m.base and m.componentes and m.principio
        assert m.dificuldade in {"iniciante", "intermediario", "avancado"}
    # o dimmer (rede eletrica) carrega aviso de seguranca
    from ghostbbs.montagens import by_id

    assert "MORTE" in by_id("DIMMER").aviso.upper()


def test_acervo_busca_por_keyword():
    from ghostbbs.montagens import buscar

    assert buscar("quero piscar um led").id == "PISCA-PISCA"
    assert buscar("preciso dimerizar a lampada da sala").id == "DIMMER"
    assert buscar("montar uma sirene de alarme").id == "SIRENE"
    assert buscar("luz correndo knight rider").id == "SEQUENCIAL"
    assert buscar("nada a ver com eletronica") is None


def test_acervo_injetado_no_prompt_do_professor():
    from ghostbbs.personas import persona_by_handle

    s = persona_by_handle("MESTRE.555").system
    # componentes fixos presentes -> consistencia de referencia
    assert "PISCA-PISCA" in s and "DIMMER" in s and "555" in s
    assert "PERIGO" in s.upper()  # alerta do dimmer no prompt


def test_ficha_render_ascii():
    from ghostbbs.montagens import by_id, ficha

    txt = ficha(by_id("PISCA-PISCA"))
    assert "PISCA-PISCA.TXT" in txt
    assert "1,44" in txt  # a formula do 555
    assert txt.isascii()  # sem acentos -> seguro no terminal de epoca


@pytest.mark.asyncio
async def test_mestre555_reply_seeds_montagem(tmp_path, monkeypatch):
    """A resposta do professor deve semear a montagem casada no prompt."""
    from ghostbbs.personas import persona_by_handle

    cfg = make_cfg(tmp_path, ghost_reply_bias=1.0)
    store = Store(cfg.db_path)
    llm = LLMClient(cfg)

    captured = {}

    async def fake_chat(messages, max_tokens=None):
        captured["user"] = messages[-1]["content"]
        return "Meu caro, monte o PISCA-PISCA com 555!"

    monkeypatch.setattr(llm, "chat", fake_chat)
    daemon = GhostDaemon(cfg, store, llm)
    daemon._pick_persona = staticmethod(lambda exclude=None: persona_by_handle("MESTRE.555"))  # type: ignore

    store.add_post("BANCADA", "CHARLES", "como faco um pisca pisca de led?")
    await daemon.tick()
    # o prompt enviado ao LLM deve mencionar a montagem casada
    assert "PISCA-PISCA" in captured["user"]
    store.close()


# --------------------------------------------------- e2e: area acervo #
@pytest.mark.asyncio
async def test_e2e_acervo_navigation(tmp_path):
    cfg = make_cfg(tmp_path)
    server = GhostBBSServer(cfg)
    await server.start()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
        c = TelnetTestClient(reader, writer)
        await c.expect(b"handle): ")
        c.send(b"CHARLES\r\n")
        await c.expect(b"Sua escolha: ")
        c.send(b"A\r\n")  # acervo
        buf = await c.expect(b"voltar): ")
        assert b"ACERVO DE MONTAGENS" in buf and b"PISCA-PISCA" in buf
        c.send(b"1\r\n")  # le a ficha 1
        buf = await c.expect(b"voltar): ")
        assert b".TXT" in buf and b"COMPONENTES" in buf
        c.send(b"\r\n")  # volta ao menu
        await c.expect(b"Sua escolha: ")
        c.send(b"G\r\n")
        await c.expect(b"NO CARRIER")
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
        except (asyncio.TimeoutError, Exception):
            pass
    finally:
        await server.stop()


# ------------------------------------------------------------- doorgame #
@pytest.mark.asyncio
async def test_doorgame_flow(tmp_path):
    cfg = make_cfg(tmp_path)
    game = DoorGame(cfg, LLMClient(cfg))
    opening = await game.start()
    assert "sala de maquinas" in opening.lower()
    reply = await game.command("IR NORTE")
    assert reply
    assert len(game.history) == 4  # 2 turnos = 4 mensagens


# ------------------------------------------------------- e2e via telnet #
class TelnetTestClient:
    """Cliente de teste com buffer persistente (evita perder prompts que
    chegam no mesmo pacote da resposta anterior)."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.buf = b""

    async def expect(self, token: bytes, timeout: float = 10.0) -> bytes:
        async with asyncio.timeout(timeout):
            while token not in self.buf:
                chunk = await self.reader.read(1024)
                if not chunk:
                    break
                self.buf += chunk
        idx = self.buf.index(token) + len(token)
        consumed, self.buf = self.buf[:idx], self.buf[idx:]
        return consumed

    def send(self, line: bytes) -> None:
        self.writer.write(line)


@pytest.mark.asyncio
async def test_e2e_telnet_login_post_and_goodbye(tmp_path):
    cfg = make_cfg(tmp_path)
    server = GhostBBSServer(cfg)
    await server.start()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
        c = TelnetTestClient(reader, writer)

        buf = await c.expect(b"handle): ")
        assert b"VORTEX-86" in buf  # banner veio antes do prompt de login
        c.send(b"CHARLES\r\n")

        buf = await c.expect(b"Sua escolha: ")
        assert b"CHARLES" in buf  # mensagem de boas-vindas com o handle

        # entra nos fóruns e posta
        c.send(b"F\r\n")
        await c.expect(b"voltar): ")
        c.send(b"GERAL\r\n")
        await c.expect(b"voltar: ")
        c.send(b"P\r\n")
        await c.expect(b"encerra.")
        c.send(b"Ola de 2026, digo, 1986!\r\n\r\n")
        buf = await c.expect(b"gravada")
        assert b"Mensagem #" in buf

        # volta ao menu e desliga
        await c.expect(b"voltar: ")
        c.send(b"\r\n")
        await c.expect(b"voltar): ")
        c.send(b"\r\n")
        await c.expect(b"Sua escolha: ")
        c.send(b"G\r\n")
        await c.expect(b"NO CARRIER")
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
        except (asyncio.TimeoutError, Exception):
            pass

        # o post humano ficou no banco e pendente para os fantasmas
        pending = server.store.pending_human_post()
        assert pending is not None and pending.author == "CHARLES"

        # um tick do daemon gera a resposta fantasma
        new_id = await server.ghosts.tick()
        ghost_post = server.store.get_post(new_id)
        assert ghost_post.is_ghost and ghost_post.reply_to == pending.id
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_e2e_chat_with_sysop(tmp_path):
    cfg = make_cfg(tmp_path)
    server = GhostBBSServer(cfg)
    await server.start()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
        c = TelnetTestClient(reader, writer)
        await c.expect(b"handle): ")
        c.send(b"CHARLES\r\n")
        await c.expect(b"Sua escolha: ")
        c.send(b"C\r\n")
        await c.expect(b"CHARLES> ")
        c.send(b"Oi Vector, tudo bem?\r\n")
        buf = await c.expect(b"VECTOR> ")
        assert b"VECTOR>" in buf
        c.send(b"/SAIR\r\n")
        await c.expect(b"Sua escolha: ")
        c.send(b"G\r\n")
        await c.expect(b"NO CARRIER")
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
        except (asyncio.TimeoutError, Exception):
            pass
    finally:
        await server.stop()
