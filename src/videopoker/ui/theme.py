"""Tema visual: paleta neon-CRT estilo máquina de cassino retrô."""
from __future__ import annotations

# Fundo preto profundo (como nas máquinas reais, faz os neons pularem)
BG_DARK = (3, 3, 10)              # preto azulado quase puro
BG_PANEL = (12, 14, 28)           # painel escuro com tom levemente azulado
BG_PANEL_LIGHT = (26, 30, 56)     # destaque

# Bevel (volume estilo Win95/cabine arcade)
BEVEL_LIGHT = (90, 110, 180)
BEVEL_DARK = (0, 0, 4)

# Textos — neons saturados
FG_AMBER = (255, 222, 0)          # amarelo-âmbar vivo (créditos, valores)
FG_GREEN = (60, 255, 80)          # verde fluorescente (labels)
FG_WHITE = (255, 255, 255)        # branco puro
FG_DIM = (130, 140, 170)

# Cores de jogo — cartas
CARD_FACE = (250, 246, 226)       # creme um pouco mais claro
CARD_BORDER = (255, 255, 255)
CARD_BACK = (70, 30, 120)         # roxo profundo (verso)
SUIT_RED = (240, 20, 30)          # vermelho mais saturado
SUIT_BLACK = (20, 20, 25)

# HOLD indicator
HOLD_YELLOW = (255, 240, 0)
HOLD_BORDER = (220, 170, 0)

# Botões
BTN_BG = (12, 20, 40)
BTN_BG_HOVER = (30, 45, 90)
BTN_BG_ACTIVE = (60, 90, 160)
BTN_BG_DISABLED = (24, 28, 44)
BTN_BORDER = (140, 180, 230)

# Mensagens
MSG_WIN = (255, 240, 0)           # amarelo puro
MSG_LOSE = (255, 70, 80)
MSG_INFO = (200, 230, 255)

# Neons puros (usados em destaques e na paytable rotativa)
NEON_MAGENTA = (255, 30, 220)     # rosa-magenta vivo
NEON_CYAN = (0, 230, 255)         # ciano elétrico
NEON_ORANGE = (255, 100, 30)      # laranja-vermelho (cabeçalhos)
NEON_YELLOW = (255, 240, 0)       # amarelo puro
NEON_GREEN = (60, 255, 80)        # verde fluorescente
NEON_PINK = (255, 80, 180)        # rosa choque

# Sequência rotativa para colorir linhas da paytable (estilo arcade)
PAYTABLE_PALETTE = (
    NEON_ORANGE,
    NEON_MAGENTA,
    NEON_GREEN,
    NEON_CYAN,
    NEON_YELLOW,
    NEON_MAGENTA,
    NEON_CYAN,
    NEON_YELLOW,
    NEON_GREEN,
    NEON_MAGENTA,
)

# Tamanhos de carta
CARD_W = 110
CARD_H = 160
CARD_RADIUS = 8
CARD_GAP = 16

# Painéis e paddings
PANEL_PADDING = 12
PANEL_RADIUS = 6

# Fontes (tamanhos). Carregadas em assets.py com fallback para SysFont.
# Ajustados para PressStart2P (cada caractere ocupa ~size px de largura).
FONT_TITLE_SIZE = 22
FONT_BIG_SIZE = 18
FONT_NORMAL_SIZE = 12
FONT_SMALL_SIZE = 9
FONT_CARD_RANK_SIZE = 24
FONT_CARD_SUIT_SIZE = 22
