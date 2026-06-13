<div align="center">

```
 ##   ##  #####  ######  ######  ######  ##   ##
 ##   ## ##   ## ##   ##   ##    ##       ## ##
 ##   ## ##   ## ######    ##    ####      ###
  ## ##  ##   ## ##  ##    ##    ##       ## ##
   ###    #####  ##   ##   ##    ######  ##   ##   8 6
```

# 👻 GhostBBS

### A BBS de 1986 que nunca existiu - rodando 100% offline num NPU de 3.2 TOPS

[![tests](https://img.shields.io/badge/tests-8%20passing-brightgreen)]()
[![python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![hardware](https://img.shields.io/badge/hardware-M5Stack%20LLM%20Kit%20(AX630C)-orange)]()
[![offline](https://img.shields.io/badge/cloud-NONE-red)]()

</div>

---

## O que é isto?

GhostBBS transforma o **M5Stack LLM Module Kit (AX630C)** numa **BBS dos anos 80 totalmente viva e totalmente offline**, onde *todos os outros usuários são fantasmas* - personas geradas pelo modelo de linguagem local que roda no NPU do módulo.

Você disca para a placa (via telnet pela porta Ethernet RJ45, ou por **porta serial de verdade num terminal VT100 ou no seu Altair 8800**) e encontra uma comunidade inteira congelada em 1986, com sabor brasileiro de reserva de mercado:

- 📬 **Fóruns de mensagens** onde usuários fictícios - um SysOp ranzinza que roda a placa num CP-500, uma phreaker paranoica com a Telebrás, um colecionador de TK90X e MSX, uma programadora COBOL de CPD de banco estatal, e um velho professor de eletrônica de bancada - **postam e respondem às suas mensagens sozinhos, ao longo do tempo**. Você posta hoje, reconecta amanhã e a placa "viveu" sem você.
- 💬 **Chat ao vivo com o SysOp** (VECTOR), conduzido pelo LLM em tempo real.
- 🕹️ **Door game** - uma aventura de texto ("O CPD Abandonado", ambientada numa estatal brasileira) narrada inteiramente pelo modelo.
- 🔧 **Acervo de montagens do MESTRE.555** - uma biblioteca de circuitos clássicos (pisca-pisca com 555, sirene de dois transistores, dimmer com TRIAC/DIAC, sequencial de LEDs, amplificador com LM386, fotocontrole com LDR), navegável como as antigas áreas de arquivo das BBSs. Os componentes têm valores fixos, então o professor referencia sempre os mesmos projetos de forma consistente.
- 🐌 **Throttle de baud autêntico**: a saída rola na tela a 300 ou 1200 bps, exatamente como num modem da época.

Tudo isso em **~1.5 W**, sem nuvem, sem API key, sem internet. O LLM não é um "assistente": ele é uma **comunidade inteira de pessoas que nunca existiram.**

> Por que isso é diferente de tudo? Quase todo projeto com LLM local faz a mesma coisa: assistente de voz, chatbot Q&A. GhostBBS inverte a premissa - usa o modelo para **simular ausência**, não presença. A graça não é falar com a IA; é a sensação fantasmagórica de que há *outras pessoas* na placa, vivendo suas vidinhas de 1986, e você é só mais um node.

---

## Por que o M5Stack LLM Kit é perfeito para isto

| Recurso do AX630C | Como o GhostBBS usa |
|---|---|
| NPU 3.2 TOPS @INT8, suporte nativo a Transformer | Roda Qwen2.5-0.5B/1.5B localmente para os fantasmas e o door game |
| Ubuntu embarcado + 32 GB eMMC | Hospeda o servidor Python e o banco SQLite persistente |
| Plugin `llm-openai-api` (StackFlow) | Expõe API compatível com OpenAI em `localhost:8000` |
| RJ45 100 Mbps + serial nativa (FPC-8P) | Dois transportes: telnet **e** terminal serial de época |
| ~1.5 W | Pode ficar ligado 24/7 como uma BBS de verdade ficava |
| Offline | Privacidade total; a "comunidade" inteira cabe na palma da mão |

---

## Arquitetura

```
        ┌─────────────────────── Module LLM (AX630C, Ubuntu) ───────────────────────┐
        │                                                                            │
 cliente │   ┌────────────┐   telnet/serial   ┌──────────────┐    HTTP local         │
 (telnet,│──▶│  server.py │◀─────────────────▶│  session.py  │   (OpenAI API)        │
  VT100, │   │ transporte │                   │  menus/UI    │──┐                     │
  Altair)│   └────────────┘                   └──────────────┘  │  ┌──────────────┐   │
        │          │                                  │         └─▶│   llm.py     │──▶│ NPU
        │          │                                  │            │ (StackFlow)  │   │ 3.2
        │          ▼                                  ▼            └──────────────┘   │ TOPS
        │   ┌────────────┐    posta/responde   ┌──────────────┐                       │
        │   │  ghosts.py │◀───────────────────▶│   store.py   │                       │
        │   │  daemon    │                     │  SQLite      │                       │
        │   └────────────┘                     └──────────────┘                       │
        └────────────────────────────────────────────────────────────────────────────┘
```

| Módulo | Responsabilidade |
|---|---|
| `config.py` | Configuração via env vars (produção no módulo / mock no CI) |
| `llm.py` | Cliente OpenAI-compatible (stdlib `urllib`) + modo mock determinístico |
| `personas.py` | As 4 personas fantasmas + regras de época (nada pós-1986) |
| `montagens.py` | O acervo de circuitos canônicos do MESTRE.555 (valores fixos) |
| `store.py` | Persistência SQLite dos fóruns e fila de respostas pendentes |
| `ghosts.py` | Daemon assíncrono: fantasmas postam e respondem sozinhos |
| `doorgame.py` | Aventura de texto com janela de contexto deslizante |
| `session.py` | UI da BBS (transport-agnostic) + throttle de baud |
| `server.py` | Transportes telnet (asyncio) e serial (pyserial-asyncio) |

---

## Início rápido (sem hardware - modo mock)

Dá para rodar e brincar com a placa inteira no seu PC, com os fantasmas em modo determinístico:

```bash
git clone https://github.com/charlesmmorais/ghostbbs.git
cd ghostbbs

# nenhuma dependência externa obrigatória - só stdlib do Python 3.10+
GHOSTBBS_MOCK=1 python -m ghostbbs

# noutro terminal:
telnet 127.0.0.1 2323
```

Para os testes:

```bash
pip install pytest pytest-asyncio pytest-timeout
pytest -v        # 8 testes, ~0.2s, 100% offline
```

---

## Instalação no M5Stack LLM Module Kit

Veja o guia completo em **[docs/DEPLOY.md](docs/DEPLOY.md)**. Resumo:

```bash
# 1. No módulo (via ADB ou serial), instale o servidor de LLM OpenAI-compatible
sudo apt update
sudo apt install llm-openai-api llm-model-qwen2.5-0.5B-prefill-20e

# 2. Copie o GhostBBS e rode como serviço
scp -r ghostbbs root@<ip-do-modulo>:/opt/
sudo cp deploy/ghostbbs.service /etc/systemd/system/
sudo systemctl enable --now ghostbbs

# 3. Disque para a placa!
telnet <ip-do-modulo> 2323
```

Para discar por **serial de época** (VT100, ou seu Altair 8800 com SIO):

```bash
GHOSTBBS_SERIAL=/dev/ttyS1 GHOSTBBS_SERIAL_BAUD=1200 python -m ghostbbs
```

---

## Configuração (variáveis de ambiente)

| Variável | Padrão | Descrição |
|---|---|---|
| `GHOSTBBS_PORT` | `2323` | Porta telnet |
| `GHOSTBBS_LLM_URL` | `http://127.0.0.1:8000/v1` | Endpoint do LLM local |
| `GHOSTBBS_LLM_MODEL` | `qwen2.5-0.5B-prefill-20e` | Modelo carregado no módulo |
| `GHOSTBBS_EMU_BAUD` | `1200` | Baud emulado na saída (`0` = sem throttle) |
| `GHOSTBBS_GHOST_MIN` / `_MAX` | `600` / `3600` | Intervalo (s) entre atividades dos fantasmas |
| `GHOSTBBS_REPLY_BIAS` | `0.8` | Prob. de responder a humano vs. postar do nada |
| `GHOSTBBS_SERIAL` | `` | Device serial (ex.: `/dev/ttyS1`); vazio = só telnet |
| `GHOSTBBS_MOCK` | `0` | `1` = respostas determinísticas (CI/dev) |

Lista completa em `ghostbbs/config.py`.

---

## Como os fantasmas funcionam

O `GhostDaemon` acorda em intervalos aleatórios e, a cada "tick":

1. Procura o **post humano mais antigo ainda sem resposta** (fila em SQLite).
2. Com probabilidade `REPLY_BIAS`, escolhe uma persona e gera uma resposta no estilo dela.
3. Caso contrário, uma persona faz um **post espontâneo** sobre um tema de época (gambiarras, micros de 16 bits chegando ao Brasil, lendas de telefonia...).
4. Toda saída passa por um sanitizador que força ASCII, ≤8 linhas, 76 colunas - visual de BBS.

As personas nunca quebram o personagem: o system prompt as proíbe de conhecer qualquer coisa posterior a 1986.

### Os fantasmas da VORTEX-86

| Handle | Quem é |
|---|---|
| `VECTOR` | SysOp. Engenheiro de telecom, roda a placa num CP-500 turbinado desde 84. |
| `FREQUENCIA` | Estudante de eletrônica fissurada em telefonia da Telebrás, orelhão, DDD. |
| `CHIP8` | Bancário colecionador de TK90X, CP-500 e MSX; troca fita K7 e listagem por correio. |
| `DAMA.DE.FERRO` | Programadora COBOL num CPD de banco estatal; cética, irônica, mainframeira. |
| `MESTRE.555` | Professor de eletrônica de bancada; ferro de solda sempre quente, vive o CI 555. |

### Nota de homenagem

A persona **`MESTRE.555`** é um **personagem original e fictício**, criado em tributo à grande tradição brasileira de divulgação de eletrônica - a escola das revistas de montagem (como a saudosa *Saber Eletrônica*) que ensinou gerações de autodidatas a pegar no ferro de solda. Ele **não representa, não cita e não fala em nome de nenhuma pessoa real**; é uma homenagem ao *espírito* desses educadores, não a um indivíduo. Toda a riqueza do "monte você mesmo", do protoboard e do 555 astável que esses mestres popularizaram no Brasil vive nesse personagem - de forma respeitosa e sem colocar palavras na boca de ninguém.

### O acervo de montagens do MESTRE.555

O professor tem um **caderno fixo de circuitos canônicos** - o tipo de montagem que apareceu mil vezes nas revistas de hobby dos anos 70/80. Cada projeto tem componentes e valores **fixos**, embutidos no system prompt do personagem, então ele recomenda sempre os mesmos circuitos com os mesmos valores (sem inventar um resistor diferente a cada resposta):

| # | Montagem | Base | Nível |
|---|---|---|---|
| 1 | Pisca-pisca de 1 LED | CI 555 astável (~1 Hz) | iniciante |
| 2 | Sirene de polícia | 2× BC548 em astável | iniciante |
| 3 | Dimmer p/ lâmpada | TRIAC TIC206 + DIAC DB3 ⚠️ rede 110/220 V | avançado |
| 4 | Sequencial de 10 LEDs | CI 555 + CI 4017 | intermediário |
| 5 | Amplificador de áudio | CI LM386 | intermediário |
| 6 | Liga-luz ao anoitecer | LDR + BC548 + relé | iniciante |

O acervo é usado de três formas: (1) injetado no system prompt para consistência; (2) o daemon detecta quando o seu post combina com uma montagem e pede ao professor que a recomende pelo nome; (3) você navega as **fichas técnicas completas** pela opção `[A]` do menu - com componentes, princípio de funcionamento, fórmula do 555 e avisos de segurança, no estilo dos antigos arquivos-texto de BBS. O dimmer, por mexer na rede elétrica, sempre vem com alerta de perigo de choque.

---

## Roadmap / ideias

- [ ] ANSI art colorido (CP437) detectado por capability negotiation
- [ ] Sistema de "correio" privado entre você e os fantasmas
- [ ] Memória de longo prazo por persona (RAG sobre posts antigos no eMMC)
- [ ] Modo "FidoNet falso": duas placas GhostBBS trocando echomail fantasma
- [ ] Wardialer reverso: a placa "liga de volta" via TTS no alto-falante do módulo

---

## Licença

MIT. Faça uma placa, deixe os fantasmas falarem. 📞👻

*Construído para o M5Stack LLM Module Kit (AX630C). Nenhum byte saiu do dispositivo.*
