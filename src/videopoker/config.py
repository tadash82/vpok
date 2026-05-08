"""Constantes globais do jogo."""
from __future__ import annotations

# Tela
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 640
FPS = 60
WINDOW_TITLE = "VIDEO POKER CLÁSSICO"

# Jogo (valores monetários — moeda fictícia)
INITIAL_CREDITS = 100.0
MIN_BET = 0.10
MAX_BET = 10.00
DEFAULT_BET = 0.10
BET_STEP = 0.10  # incremento de cada `+ APOSTA` / `- APOSTA`

# Cartas
HAND_SIZE = 5
DECK_SIZE = 52
