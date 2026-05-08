"""Máquina de estados do jogo."""
from __future__ import annotations

from enum import Enum, auto


class GameState(Enum):
    IDLE = auto()              # esperando o jogador definir/confirmar a aposta
    BET_PLACED = auto()        # aposta confirmada, esperando DEAL
    DEALT = auto()             # 5 cartas na mesa, escolhendo HOLDs
    DRAWN = auto()             # troca feita, mão final pronta para avaliação
    EVALUATED = auto()         # rodada avaliada; se ganhou, prêmio em pending — DOBRAR ou LEVAR
    DOUBLE_OFFERED = auto()    # carta da dobra virada, esperando BIG/MINI/LEVAR
    DOUBLE_REVEALED = auto()   # carta revelada, mostrando outcome (win/tie/lose)
    GAME_OVER = auto()         # créditos zerados, sem aposta possível


class InvalidTransitionError(RuntimeError):
    """Levantada ao tentar uma operação não permitida no estado atual."""

    def __init__(self, current: GameState, operation: str) -> None:
        super().__init__(
            f"operação '{operation}' não permitida no estado {current.name}"
        )
        self.current = current
        self.operation = operation
