# Guia de Deploy — GhostBBS no M5Stack LLM Module Kit (AX630C)

Este guia leva você de uma placa recém-tirada da caixa até uma BBS fantasma no ar.

## 0. Pré-requisitos

- M5Stack LLM Module Kit (Module LLM + Module13.2 LLM Mate)
- Cabo USB-C (para alimentação e ADB/serial de debug)
- Cabo Ethernet (RJ45) ligado à sua rede, **ou** um terminal serial / adaptador FTDI para a experiência de época
- Um host (Linux/macOS/Windows) com `adb` e `ssh`/`scp`

## 1. Ligando e acessando o módulo

O Module LLM roda um Ubuntu embarcado. Conecte o USB-C do Module Mate e acesse via ADB:

```bash
adb devices
adb shell          # você cai num shell do Ubuntu do módulo
```

Descubra o IP do módulo (se usar Ethernet):

```bash
ip addr show eth0
```

A partir daqui você pode usar `ssh root@<ip>` em vez de ADB, se preferir.
A senha padrão e detalhes de rede estão na documentação oficial do StackFlow:
https://docs.m5stack.com/en/stackflow/overview

## 2. Instalando o runtime de LLM (StackFlow / OpenAI API)

O módulo usa o framework **StackFlow** com pacotes `apt`. Instale o plugin que
expõe a API compatível com OpenAI e um modelo pequeno (cabe nos ~3 GB
reservados para aceleração):

```bash
sudo apt update
sudo apt install llm-sys llm-llm llm-openai-api

# escolha UM modelo (0.5B é o mais leve e responde rápido):
sudo apt install llm-model-qwen2.5-0.5B-prefill-20e
# alternativas mais capazes (mais lentas):
# sudo apt install llm-model-qwen2.5-1.5B-ax630c
```

> Os nomes exatos dos pacotes podem variar conforme a versão do firmware.
> Liste o que há disponível com: `apt list 2>/dev/null | grep -i llm-model`

Inicie o serviço OpenAI-API (normalmente sobe em `127.0.0.1:8000`):

```bash
sudo systemctl enable --now llm-openai-api
# teste:
curl http://127.0.0.1:8000/v1/models
```

Anote o **id do modelo** retornado — é o valor de `GHOSTBBS_LLM_MODEL`.

## 3. Copiando o GhostBBS para o módulo

Do seu host:

```bash
scp -r ghostbbs root@<ip-do-modulo>:/opt/ghostbbs
```

(ou `adb push ghostbbs /opt/ghostbbs`)

O GhostBBS usa **apenas a biblioteca padrão do Python** para o caminho telnet,
então não há `pip install` obrigatório. Para o caminho serial:

```bash
pip3 install pyserial-asyncio
```

## 4. Testando manualmente

No módulo:

```bash
cd /opt/ghostbbs
GHOSTBBS_LLM_MODEL="qwen2.5-0.5B-prefill-20e" python3 -m ghostbbs
```

Do seu host, na mesma rede:

```bash
telnet <ip-do-modulo> 2323
```

Você deve ver o banner da VORTEX-86. Poste algo num fórum, espere alguns
minutos (ou reduza `GHOSTBBS_GHOST_MIN`/`MAX` para testar), e veja um fantasma
responder.

## 5. Rodando como serviço (systemd)

Copie o unit file e ajuste o IP/modelo:

```bash
sudo cp /opt/ghostbbs/deploy/ghostbbs.service /etc/systemd/system/
sudoedit /etc/systemd/system/ghostbbs.service   # ajuste Environment= se preciso
sudo systemctl daemon-reload
sudo systemctl enable --now ghostbbs
sudo journalctl -u ghostbbs -f                  # logs ao vivo
```

## 6. (Opcional) Discando por serial de época

O Module Mate expõe a serial do core via FPC-8P / RJ45. Para usar um terminal
VT100 real, um PuTTY serial, ou **um Altair 8800 com placa SIO**:

1. Descubra qual device serial o módulo expõe internamente (ex.: `/dev/ttyS1`).
2. Rode:

```bash
GHOSTBBS_SERIAL=/dev/ttyS1 \
GHOSTBBS_SERIAL_BAUD=1200 \
GHOSTBBS_EMU_BAUD=0 \
python3 -m ghostbbs
```

> Quando o transporte já é serial e roda no baud real (1200), desligue o
> throttle emulado (`GHOSTBBS_EMU_BAUD=0`) — o fio já faz o trabalho. Para
> telnet, mantenha `GHOSTBBS_EMU_BAUD=1200` para recriar a estética.

Configure o terminal/Altair para **1200 8N1, sem controle de fluxo**.
Aperte ENTER e a portadora "conecta".

## 7. Ajuste fino de desempenho

- O Qwen2.5-0.5B responde em ~1–4 s por turno no AX630C. Mantenha
  `GHOSTBBS_LLM_MAXTOK` baixo (≤256) para respostas ágeis estilo BBS.
- O door game usa janela de contexto de 6 turnos para não estourar o modelo.
- Se quiser fantasmas mais "vivos" durante demos, use
  `GHOSTBBS_GHOST_MIN=20 GHOSTBBS_GHOST_MAX=60`.

## Troubleshooting

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Falha ao consultar o LLM local` nos logs | serviço OpenAI-API não está no ar | `systemctl status llm-openai-api`; `curl localhost:8000/v1/models` |
| Fantasmas nunca postam | intervalo muito alto / LLM lento | reduza `GHOSTBBS_GHOST_MIN/MAX` e cheque logs |
| Telnet conecta mas nada aparece | cliente mandando IAC demais | use `nc`/SyncTERM, ou veja o filtro IAC em `server.py` |
| Serial só mostra lixo | baud divergente | iguale `GHOSTBBS_SERIAL_BAUD` ao baud do terminal |
| Texto rola rápido demais | throttle desligado | `GHOSTBBS_EMU_BAUD=1200` (ou 300) |
