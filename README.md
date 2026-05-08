# Video Poker Clássico

Video Poker single-player (Five-Card Draw) em Python + Pygame, com estética retrô anos 80/90.

Baseado no documento de visão em `docs/poker.txt`.

## Download (jogar sem instalar nada)

Versões prontas pra Windows e Linux ficam em **[github.com/tadash82/vpok/releases/latest](https://github.com/tadash82/vpok/releases/latest)**:

- **`videopoker-windows.exe`** — clique duplo e jogue.
- **`videopoker-linux`** — `chmod +x videopoker-linux && ./videopoker-linux`.

Os binários incluem o Python embutido + todas as fontes — não precisa instalar nada.

## Instalação a partir do código

```bash
pip install -r requirements.txt
```

Requer Python 3.10+. Em distribuições com PEP 668 (Ubuntu 24.04+) use `--user --break-system-packages` ou um virtualenv.

## Como jogar

```bash
python3 run.py
```

### Controles

#### Fase de poker

| Ação | Mouse | Teclado |
|---|---|---|
| Ajustar aposta | `- APOSTA` / `+ APOSTA` / `APOSTA MAX` | `+` / `-` |
| Distribuir | `DISTRIBUIR` | `Enter` ou `Espaço` |
| Marcar/desmarcar HOLD | clique na carta ou no botão HOLD | `1` a `5` |
| Trocar | `TROCAR` | `Enter` ou `Espaço` |
| Próxima rodada | `PROXIMA` | `Enter` ou `Espaço` |
| Reiniciar (após GAME OVER) | — | `R` |
| Sair | — | `Esc` |

#### Fase de dobra (após uma vitória)

| Ação | Mouse | Teclado |
|---|---|---|
| Iniciar dobra | `DOBRAR` | `D` |
| Apostar BIG (> 7) | `BIG (>7)` | `B` |
| Apostar MINI (< 7) | `MINI (<7)` | `M` |
| Aposta cheia (rank + naipe) | `CHEIO` | `C` |
| Selecionar rank/naipe | clique nos botões | — |
| Confirmar aposta cheia | `CONFIRMAR` | `Enter` |
| Voltar do CHEIO sem apostar | `VOLTAR` | `Backspace` |
| Abrir carta de uma vez | `ABRIR RAPIDO` | `A` |
| Abrir carta passo a passo | `ABRIR` | `↑` (seta pra cima) |
| Levar prêmio | `LEVAR` | `L` ou `Enter` |
| Continuar (após perder a dobra) | `CONTINUAR` | `Enter` |

## Regra de dobra (Double Up)

Após uma rodada de poker premiada, o prêmio fica em risco como **PRÊMIO PENDENTE**. O jogador pode:

- **LEVAR** o prêmio para o saldo, ou
- **DOBRAR**: o sistema vira uma carta do baralho remanescente. Há três modalidades de aposta.

#### Modalidade BIG / MINI (2x)

Aposta-se que a carta será maior ou menor que 7.

| Carta da dobra | Resultado |
|---|---|
| Acertou (lado apostado) | Prêmio × 2 — pode dobrar de novo ou levar |
| Errou | Perde o prêmio |
| Saiu **7** | Empate — sorteia outra carta com prêmio intacto |

#### Modalidade CHEIO (5x ou 10x)

Aposta-se em um **rank exato** (2-A) E em um **naipe exato** (♥, ♦, ♣, ♠).

| Carta da dobra | Resultado |
|---|---|
| Acertou rank E naipe | Prêmio × 10 — pode dobrar de novo ou levar |
| Acertou só o rank (naipe errado) | Prêmio × 5 — pode dobrar de novo ou levar |
| Rank errado | Perde o prêmio |

Não há empate em 7 nesta modalidade — o pivô é exclusivo de BIG/MINI.

#### Regras gerais da dobra

A dobra usa o mesmo baralho da rodada de poker (sem repor cartas). Pode-se dobrar até esgotar as cartas restantes — quando o baralho zera, o sistema força levar o prêmio. As cartas reveladas durante as dobras ficam visíveis no painel **HISTÓRICO**.

#### Auto-continuação

Após um acerto (BIG/MINI/CHEIO) ou empate, o jogo **dispara automaticamente** a próxima dobra depois de uma pequena pausa (≈ 1.4 s). A sequência continua até você **errar** (perde tudo) ou clicar **LEVAR** durante a janela.

#### Como abrir a carta

Depois de clicar em BIG, MINI ou CHEIO, a carta fica na mesa virada para baixo. Aparecem **dois botões** no lugar dos botões de aposta:

- **ABRIR RAPIDO** (`A`): descobre a carta de uma vez só. **Trava** o modo rápido durante a sequência atual: as próximas BIG/MINI/CHEIO já abrem direto, sem pedir clique extra, e o intervalo entre dobras é reduzido (≈ 0.5 s no lugar de 1.4 s).
- **ABRIR** (`↑`): cada clique levanta um pedaço da carta (de baixo pra cima). São 5 cliques para a carta ficar totalmente visível — ideal para criar suspense. Voltar a clicar em ABRIR **destrava** o modo rápido.

O lock também é desfeito ao **LEVAR** o prêmio ou ao **perder** uma dobra (a próxima sequência começa em modo manual de novo).

## Apostas e combinações

Aposta vai de **0.10** (mínima) até **10.00** (máxima), em incrementos de 0.10.

Multiplicadores aplicados sobre a aposta — calibrados para que aposta mínima (0.10) produza os "valores de referência" do item 8 do documento de visão:

| Combinação | Multiplicador | Prêmio @ aposta 0.10 | Prêmio @ aposta 1.00 |
|---|---:|---:|---:|
| ROYAL STRAIGHT | 500× | 50.00 | 500.00 |
| STRAIGHT FLUSH | 150× | 15.00 | 150.00 |
| QUADRA | 60× | 6.00 | 60.00 |
| FULL HOUSE | 10× | 1.00 | 10.00 |
| FLUSH | 7× | 0.70 | 7.00 |
| STRAIGHT | 5× | 0.50 | 5.00 |
| TRINCA | 3× | 0.30 | 3.00 |
| 2 PARES | 2× | 0.20 | 2.00 |

Combinações marcadas como "A DEFINIR" no documento (VEGAS ROYAL, FIGURAS, multiplicadores especiais Maior/Menor que 7, Cheia, etc.) ficaram fora desta versão; pontos de extensão estão preparados em `src/videopoker/domain/evaluator.py` (lista `DETECTORS`) e `src/videopoker/domain/rules/extra.py`.

## Tela cheia / janela redimensionável

- **F11** alterna entre janela e tela cheia (atalho configurável).
- A janela pode ser redimensionada arrastando as bordas — o conteúdo escala mantendo aspect ratio (com barras pretas se a proporção da janela for diferente de 3:2).
- Internamente o jogo sempre desenha num canvas lógico de 960×640 e o pygame escala pra qualquer resolução, então o layout não quebra em nenhum tamanho.

## Configuração de controles

Pressione **F2** ou clique no botão **OPÇÕES** (canto superior direito) para abrir a tela de configuração. Você pode:

- **Rebindar qualquer ação**: clique em `REBIND` ao lado da ação e pressione a nova tecla
- **Restaurar padrão**: botão `RESTAURAR PADRAO` reverte tudo
- **ESC** é reservado (sair do jogo) e não pode ser usado como binding

As configurações são salvas em `~/.config/videopoker/keybindings.json` (Linux/macOS) ou `%APPDATA%/videopoker/keybindings.json` (Windows) e persistem entre execuções.

## Sons

Os sons são gerados programaticamente (sem assets externos), com timbres curtos estilo arcade:

| Evento | Som |
|---|---|
| Vitória na rodada de poker | Arpejo ascendente C-E-G-C |
| Derrota na rodada de poker | Dois tons descendentes |
| Iniciar dobra | Bling de aviso (2 tons) |
| Acerto na dobra (BIG/MINI/CHEIO) | **Sino** que sobe de pitch a cada acerto consecutivo (~3 semitons por acerto, cap em 12 níveis) |
| Empate (carta = 7 em BIG/MINI) | Sino neutro sem progressão |
| Erro na dobra | Tons descendentes; o pitch do sino reseta |
| Levar prêmio | Tinido tipo caixa-registradora |

Implementação em `src/videopoker/ui/sound.py`. Se o áudio não puder ser inicializado, o jogo segue silencioso sem erro.

## Arquitetura

```
src/videopoker/
  domain/        — cartas, baralho, avaliador, paytable (Python puro, sem Pygame)
  game/          — máquina de estados e sessão
  ui/            — janela, cena, widgets (único lugar com Pygame)
assets/
  fonts/         — Press Start 2P + VT323 (TTF)
  icon.ico       — ícone do executável (gerado por scripts/make_icon.py)
  icon.png       — ícone da janela do pygame
scripts/
  make_icon.py   — gerador procedural do ícone
  cli_demo.py    — smoke test estatístico do motor
.github/workflows/
  build.yml      — CI: testes + PyInstaller (Win/Linux) + release em tags v*
```

- **Domínio sem Pygame**: o motor é testável isoladamente e independente de UI.
- **Máquina de estados explícita**: `IDLE → BET_PLACED → DEALT → DRAWN → EVALUATED → (DOUBLE_OFFERED ⇄ DOUBLE_REVEALED)* → IDLE`. Em caso de saldo zerado, transita para `GAME_OVER`.
- **RNG idôneo**: `random.SystemRandom()` por padrão; seed injetável em testes.
- **Detectores ordenados**: `evaluator.py` aplica uma lista de detectores do mais raro pro mais comum — adicionar uma nova combinação é inserir um item, não refatorar.

## Testes

```bash
python3 -m pytest tests/
```

79 testes cobrindo cartas, baralho, avaliador (todas as combinações + edge cases como wheel A-2-3-4-5), paytable, máquina de estados, fluxo de dobra (BIG/MINI/CHEIO + auto-continuação) e calibração da economia.

## Distribuir o jogo (executável standalone)

Para gerar um executável que roda sem instalar Python (ideal pra mandar pros amigos):

```bash
pip install -r requirements-build.txt
pyinstaller videopoker.spec
```

A saída fica em `dist/`:

| Plataforma | Arquivo | Tamanho típico |
|---|---|---|
| Linux | `dist/videopoker` | ~ 18 MB (build local) / ~ 32 MB (CI) |
| Windows | `dist/videopoker.exe` | ~ 17-25 MB |

O mesmo `videopoker.spec` funciona em ambas as plataformas — basta rodar `pyinstaller videopoker.spec` no SO de destino. As fontes em `assets/fonts/`, o ícone em `assets/icon.ico` e o código fonte ficam embutidos no binário.

**Para Windows**: rode o comando acima dentro de uma máquina/VM Windows com Python 3.10+ instalado. PyInstaller não faz cross-compilation a partir do Linux — use o GitHub Actions (próxima seção) se você só tem Linux.

> Configurações do jogador (`keybindings.json`) ficam em `~/.config/videopoker/` (Linux/macOS) ou `%APPDATA%\videopoker\` (Windows), independente do executável.

### Ícone do jogo

O ícone do executável e da janela é gerado proceduralmente por `scripts/make_icon.py` (Pillow). Para ajustar a arte (paleta, formas), edite o script e rode novamente:

```bash
python3 scripts/make_icon.py
```

Saída: `assets/icon.png` (256×256, ícone da janela do pygame) e `assets/icon.ico` (multi-resolução 16/32/48/64/128/256, usado pelo PyInstaller no Windows e mostrado na taskbar/Explorer).

### Build automatizado (GitHub Actions)

O workflow em `.github/workflows/build.yml` gera os binários **Windows e Linux em paralelo** sempre que você fizer push ou criar uma tag:

| Trigger | O que acontece |
|---|---|
| `push` em `main`/`master` | Roda testes, gera os dois binários, sobe como artifacts |
| Pull request | Roda testes e build (sem subir release) |
| `workflow_dispatch` | Roda manualmente pelo botão **Run workflow** na aba Actions |
| Tag `v*` (ex.: `v1.0.0`) | Faz tudo acima **+** cria uma Release no GitHub com os binários anexados (`videopoker-windows.exe` e `videopoker-linux`) |

Para baixar uma build manual (sem fazer release):

1. GitHub → aba **Actions** → último workflow verde
2. Seção **Artifacts** no fim da página
3. Baixe `videopoker-windows` (.exe) ou `videopoker-linux`

Para publicar uma nova versão pública:

```bash
git tag v0.2.0
git push vpok v0.2.0           # ou: git push origin v0.2.0 — use o nome do seu remote
```

Em ~5 minutos uma Release aparece em **[github.com/tadash82/vpok/releases](https://github.com/tadash82/vpok/releases)** com `videopoker-windows.exe` e `videopoker-linux` anexados, prontos pra compartilhar via link.

## Smoke test do motor

```bash
python3 scripts/cli_demo.py -n 50000 --seed 42
```

Simula N rodadas sem trocar cartas e imprime distribuição estatística + RTP estimado — útil para validar RNG e detector.
