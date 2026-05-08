"""Baralho de 52 cartas com RNG injetável."""
from __future__ import annotations

import random
from typing import Iterable

from .card import Card, Rank, Suit


def _build_full_deck() -> list[Card]:
    return [Card(rank, suit) for suit in Suit for rank in Rank]


class EmptyDeckError(RuntimeError):
    """Levantada ao tentar sacar de um baralho esgotado."""


class Deck:
    """Baralho de 52 cartas únicas, embaralhado por um RNG injetável.

    Por padrão usa random.SystemRandom() (auditável). Em testes, passe
    random.Random(seed) para determinismo.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.SystemRandom()
        self._cards: list[Card] = _build_full_deck()
        self.shuffle()

    def shuffle(self) -> None:
        self._rng.shuffle(self._cards)

    def draw(self, n: int = 1) -> list[Card]:
        if n < 0:
            raise ValueError("n deve ser >= 0")
        if n > len(self._cards):
            raise EmptyDeckError(
                f"baralho tem {len(self._cards)} cartas, pediu {n}"
            )
        drawn = self._cards[:n]
        self._cards = self._cards[n:]
        return drawn

    @property
    def remaining(self) -> int:
        return len(self._cards)

    def peek(self) -> Iterable[Card]:
        """Retorna iterável das cartas remanescentes (apenas leitura — debug/testes)."""
        return tuple(self._cards)
