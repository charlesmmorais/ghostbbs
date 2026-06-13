"""O acervo de montagens canonicas do MESTRE.555.

Um pequeno caderno de circuitos classicos da eletronica de hobby, com
componentes e valores FIXOS. Esse acervo e:

  1. injetado no system prompt do MESTRE.555, para que ele referencie
     sempre os mesmos projetos com os mesmos componentes (consistencia);
  2. exposto ao usuario humano como uma area navegavel da BBS (as antigas
     bibliotecas de arquivos-texto das placas).

Texto sem acentos de proposito: as fichas sao transmitidas em ASCII puro
para terminais de epoca.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class Montagem:
    id: str                       # slug/handle, ex.: "PISCA-PISCA"
    nome: str
    dificuldade: str              # iniciante / intermediario / avancado
    base: str                     # bloco principal (CI/transistor)
    componentes: Tuple[str, ...]
    principio: str                # como funciona, em 1-3 frases
    montagem: str                 # notas de montagem
    formula: str = ""             # opcional
    aviso: str = ""               # opcional (seguranca)
    palavras: Tuple[str, ...] = field(default_factory=tuple)  # keywords p/ busca


ACERVO: Tuple[Montagem, ...] = (
    Montagem(
        id="PISCA-PISCA",
        nome="Pisca-pisca de 1 LED",
        dificuldade="iniciante",
        base="CI 555 em astavel",
        componentes=(
            "1x CI 555",
            "R1 = 1k (pino 7 ao +V)",
            "R2 = 68k (pino 7 aos pinos 6 e 2)",
            "C = 10uF eletrolitico (pino 2 ao terra)",
            "LED comum + resistor de 470 ohm no pino 3",
            "Bateria de 9V",
        ),
        principio=(
            "O 555 carrega C por R1+R2 e descarrega por R2, gerando uma onda "
            "quadrada no pino 3 que acende e apaga o LED ritmadamente."
        ),
        montagem=(
            "Pino 1 ao terra, pino 8 e 4 ao +9V, pinos 2 e 6 juntos no ponto "
            "R2/C, pino 7 entre R1 e R2. Saida no pino 3 para o LED com 470 ohm."
        ),
        formula="f = 1,44 / ((R1 + 2*R2) * C). Com 1k, 68k e 10uF da ~1 Hz.",
        palavras=("pisca", "pisca-pisca", "led", "piscar", "blink", "intermitente",
                  "555 astavel", "oscilador", "lampejo"),
    ),
    Montagem(
        id="SIRENE",
        nome="Sirene de policia (sobe-desce)",
        dificuldade="iniciante",
        base="Dois transistores BC548 em multivibrador astavel",
        componentes=(
            "2x transistor BC548",
            "2x resistor de 4k7 (bases)",
            "2x resistor de 470 ohm (coletores)",
            "2x capacitor de 10nF (acoplamento, define o tom)",
            "1x eletrolitico de 100uF (faz o tom subir e descer)",
            "Alto-falante de 8 ohm",
            "Botao de pressao e bateria de 9V",
        ),
        principio=(
            "Os dois transistores formam um oscilador de audio. Ao apertar o "
            "botao, o eletrolitico de 100uF carrega e varia a tensao de "
            "alimentacao do oscilador, fazendo a frequencia subir; ao soltar, "
            "ele descarrega e o tom desce - o classico uou-uou da sirene."
        ),
        montagem=(
            "Astavel padrao de 2 transistores; o alto-falante vai no coletor de "
            "um deles. O 100uF entra em serie na alimentacao, comandado pelo botao."
        ),
        palavras=("sirene", "sirena", "alarme", "uou", "policia", "som", "apito",
                  "alto-falante", "alto falante"),
    ),
    Montagem(
        id="DIMMER",
        nome="Dimmer para lampada incandescente",
        dificuldade="avancado",
        base="TRIAC + DIAC (controle de fase da rede)",
        componentes=(
            "1x TRIAC TIC206 (ou BT136)",
            "1x DIAC DB3 (dispara em ~32V)",
            "1x potenciometro de 100k",
            "1x resistor de 10k em serie com o pot",
            "1x capacitor de 100nF / 250V (poliester)",
            "Lampada incandescente (NAO serve para LED nem fluorescente)",
        ),
        principio=(
            "A rede RC (pot + capacitor) defasa a tensao da rede. Quando o "
            "capacitor atinge a tensao de disparo do DIAC (~32V), ele dispara o "
            "gate do TRIAC, que conduz ate o fim do semiciclo. Girando o "
            "potenciometro muda-se o angulo de disparo - e portanto o brilho."
        ),
        montagem=(
            "TRIAC em serie com a lampada e a rede. Gate disparado pelo DIAC, "
            "alimentado pelo ponto do capacitor. Monte numa caixa fechada e isolada."
        ),
        aviso=(
            "*** PERIGO DE MORTE *** Este circuito opera DIRETAMENTE na tensao "
            "da rede (110/220V). Choque eletrico pode MATAR. So monte se tiver "
            "experiencia, sempre com tudo DESLIGADO da tomada, dentro de caixa "
            "isolada, e NUNCA toque no circuito energizado. Iniciante: peca ajuda."
        ),
        palavras=("dimmer", "dimerizar", "dimer", "brilho", "lampada", "triac",
                  "diac", "controle de luz", "intensidade", "luz"),
    ),
    Montagem(
        id="SEQUENCIAL",
        nome="Sequencial de 10 LEDs (luz correndo)",
        dificuldade="intermediario",
        base="CI 555 (clock) + CI 4017 (contador decada)",
        componentes=(
            "1x CI 555 (gera o clock)",
            "1x CI 4017 (decada Johnson)",
            "10x LED + 10x resistor de 470 ohm",
            "R e C do 555 para ajustar a velocidade (ex.: 47k e 1uF)",
            "Alimentacao de 5 a 12V",
        ),
        principio=(
            "O 555 gera pulsos de clock. A cada pulso, o 4017 avanca e acende "
            "uma de suas 10 saidas por vez, em sequencia, criando o efeito de "
            "luz correndo. Realimentando a saida certa no reset encurta-se a fila."
        ),
        montagem=(
            "Saida do 555 (pino 3) no clock do 4017 (pino 14). As 10 saidas Q0..Q9 "
            "vao cada uma a um LED com 470 ohm. Pino 13 (inibe) ao terra."
        ),
        formula="Velocidade = clock do 555. Mais C, mais lento o desfile.",
        palavras=("sequencial", "correndo", "knight rider", "4017", "desfile",
                  "chaser", "leds em sequencia", "pisca sequencial", "correr"),
    ),
    Montagem(
        id="AMPLI-LM386",
        nome="Amplificador de audio com LM386",
        dificuldade="intermediario",
        base="CI LM386 (amplificador de potencia de audio)",
        componentes=(
            "1x CI LM386",
            "Potenciometro de 10k (volume, na entrada)",
            "Capacitor de 10uF (acoplamento de entrada)",
            "Capacitor de 220uF (acoplamento de saida ao alto-falante)",
            "Rede de 10 ohm + 47nF (Zobel) na saida",
            "Capacitor de 10uF entre pinos 1 e 8 para ganho 200",
            "Alto-falante de 8 ohm, alimentacao de 9V",
        ),
        principio=(
            "O LM386 amplifica um sinal de audio fraco o suficiente para mover "
            "um alto-falante de 8 ohm. O ganho e 20 por padrao e sobe para 200 "
            "colocando um capacitor de 10uF entre os pinos 1 e 8."
        ),
        montagem=(
            "Entrada no pino 3 (via volume e 10uF), pino 2 ao terra, pino 6 ao "
            "+V, pino 4 ao terra, saida no pino 5 ao alto-falante via 220uF."
        ),
        palavras=("amplificador", "ampli", "audio", "som", "lm386", "volume",
                  "alto-falante", "musica", "amplificar"),
    ),
    Montagem(
        id="FOTOCONTROLE",
        nome="Liga-luz automatico ao anoitecer (LDR)",
        dificuldade="iniciante",
        base="LDR + transistor BC548 + rele",
        componentes=(
            "1x LDR (foto-resistor)",
            "1x trimpot de 100k (ajuste do ponto de disparo)",
            "1x transistor BC548",
            "1x rele de 6V",
            "1x diodo 1N4148 (roda-livre sobre o rele)",
            "Alimentacao de 9V",
        ),
        principio=(
            "O LDR e o trimpot formam um divisor de tensao. Quando escurece, a "
            "resistencia do LDR sobe, a tensao na base do transistor muda e ele "
            "satura, energizando o rele que liga a lampada. De dia, desliga."
        ),
        montagem=(
            "Divisor LDR/trimpot na base do BC548. Rele do coletor ao +V, com o "
            "1N4148 invertido em paralelo para proteger o transistor."
        ),
        aviso=(
            "Se o rele chavear tensao da rede para a lampada, vale o mesmo "
            "cuidado do dimmer: isole bem o lado de 110/220V."
        ),
        palavras=("ldr", "sensor de luz", "fotocelula", "fotocontrole", "rele",
                  "anoitecer", "escuro", "automatico", "noturno", "foto"),
    ),
)


# --------------------------------------------------------------------- #
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def by_id(mid: str) -> Optional[Montagem]:
    alvo = _norm(mid)
    for m in ACERVO:
        if _norm(m.id) == alvo:
            return m
    return None


def buscar(texto: str) -> Optional[Montagem]:
    """Acha a montagem mais relevante para um texto livre, por keywords."""
    t = _norm(texto)
    melhor: Optional[Montagem] = None
    melhor_pontos = 0
    for m in ACERVO:
        pontos = sum(1 for p in m.palavras if _norm(p) in t)
        # nome/id tambem contam
        if _norm(m.id) in t or _norm(m.nome) in t:
            pontos += 2
        if pontos > melhor_pontos:
            melhor, melhor_pontos = m, pontos
    return melhor if melhor_pontos > 0 else None


def catalogo_compacto() -> str:
    """Resumo de uma linha por montagem, para o system prompt do MESTRE.555."""
    linhas = []
    for i, m in enumerate(ACERVO, 1):
        comps = "; ".join(m.componentes[:4])
        risco = "  [PERIGO: rede 110/220V]" if m.aviso and "MORTE" in m.aviso else ""
        linhas.append(f"{i}. {m.id} ({m.base}): {comps}.{risco}")
    return "\n".join(linhas)


def ficha(m: Montagem, width: int = 70) -> str:
    """Ficha completa da montagem, em ASCII estilo arquivo-texto de BBS."""
    bar = "=" * width
    out = [
        bar,
        f"  MONTAGEM: {m.nome}",
        f"  ARQUIVO : {m.id}.TXT   NIVEL: {m.dificuldade.upper()}",
        f"  BASE    : {m.base}",
        bar,
        "",
        "COMPONENTES:",
    ]
    out += [f"  - {c}" for c in m.componentes]
    out += ["", "COMO FUNCIONA:", f"  {m.principio}"]
    out += ["", "MONTAGEM:", f"  {m.montagem}"]
    if m.formula:
        out += ["", "FORMULA:", f"  {m.formula}"]
    if m.aviso:
        out += ["", m.aviso]
    out += ["", "-- MESTRE.555, na bancada desde sempre. Monte voce mesmo! --", bar]
    return "\n".join(out)
