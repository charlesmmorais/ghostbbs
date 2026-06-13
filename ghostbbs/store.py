"""Fóruns de mensagens — persistência em SQLite.

Acesso síncrono e simples (sqlite3 da stdlib); o servidor chama via
asyncio.to_thread quando necessário. Volume de dados é minúsculo.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import List, Optional

DEFAULT_BOARDS = [
    ("GERAL", "Papo de modem, avisos da placa"),
    ("HARDWARE", "Micros nacionais, perifericos, gambiarras"),
    ("SOFTWARE", "BASIC, COBOL, troca de listagens e programas"),
    ("BANCADA", "Eletronica, montagens, ferro de solda, 555"),
    ("FONE", "Telebras, DDD, lendas da linha"),
]


@dataclass
class Post:
    id: int
    board: str
    author: str
    is_ghost: bool
    body: str
    reply_to: Optional[int]
    ts: float


class Store:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init()

    def _init(self) -> None:
        c = self.conn
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS boards(
                name TEXT PRIMARY KEY,
                descr TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS posts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board TEXT NOT NULL REFERENCES boards(name),
                author TEXT NOT NULL,
                is_ghost INTEGER NOT NULL DEFAULT 0,
                body TEXT NOT NULL,
                reply_to INTEGER,
                ts REAL NOT NULL,
                ghost_replied INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        for name, descr in DEFAULT_BOARDS:
            c.execute("INSERT OR IGNORE INTO boards(name, descr) VALUES(?,?)", (name, descr))
        c.commit()

    # ------------------------------------------------------------------ #
    def boards(self) -> List[tuple[str, str, int]]:
        rows = self.conn.execute(
            """SELECT b.name, b.descr, COUNT(p.id)
               FROM boards b LEFT JOIN posts p ON p.board = b.name
               GROUP BY b.name ORDER BY b.rowid"""
        ).fetchall()
        return [(r[0], r[1], r[2]) for r in rows]

    def add_post(
        self,
        board: str,
        author: str,
        body: str,
        *,
        is_ghost: bool = False,
        reply_to: Optional[int] = None,
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO posts(board, author, is_ghost, body, reply_to, ts)"
            " VALUES(?,?,?,?,?,?)",
            (board, author, int(is_ghost), body, reply_to, time.time()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def posts(self, board: str, limit: int = 20) -> List[Post]:
        rows = self.conn.execute(
            "SELECT id, board, author, is_ghost, body, reply_to, ts FROM posts"
            " WHERE board=? ORDER BY id DESC LIMIT ?",
            (board, limit),
        ).fetchall()
        return [Post(r[0], r[1], r[2], bool(r[3]), r[4], r[5], r[6]) for r in reversed(rows)]

    def get_post(self, post_id: int) -> Optional[Post]:
        r = self.conn.execute(
            "SELECT id, board, author, is_ghost, body, reply_to, ts FROM posts WHERE id=?",
            (post_id,),
        ).fetchone()
        return Post(r[0], r[1], r[2], bool(r[3]), r[4], r[5], r[6]) if r else None

    # --- fila para o daemon fantasma --------------------------------- #
    def pending_human_post(self) -> Optional[Post]:
        """Post humano mais antigo ainda não respondido por um fantasma."""
        r = self.conn.execute(
            "SELECT id, board, author, is_ghost, body, reply_to, ts FROM posts"
            " WHERE is_ghost=0 AND ghost_replied=0 ORDER BY id LIMIT 1"
        ).fetchone()
        return Post(r[0], r[1], r[2], bool(r[3]), r[4], r[5], r[6]) if r else None

    def mark_ghost_replied(self, post_id: int) -> None:
        self.conn.execute("UPDATE posts SET ghost_replied=1 WHERE id=?", (post_id,))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
