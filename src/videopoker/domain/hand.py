"""Mão do jogador: 5 cartas + marcações de HOLD."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .card import Card

HAND_SIZE = 5


@dataclass
class Hand:
    """Mão de exatamente 5 cartas com marcações de HOLD por posição.

    Holds é um conjunto de índices (0..4) das cartas a manter na troca.
    Mantemos a posição original (replace_unheld preserva ordem visual).
    """

    cards: list[Card]
    holds: set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        if len(self.cards) != HAND_SIZE:
            raise ValueError(f"mão deve ter {HAND_SIZE} cartas, recebeu {len(self.cards)}")
        if any(i < 0 or i >= HAND_SIZE for i in self.holds):
            raise ValueError(f"holds devem estar em 0..{HAND_SIZE - 1}")

    def toggle_hold(self, index: int) -> None:
        if index < 0 or index >= HAND_SIZE:
            raise ValueError(f"index fora da faixa 0..{HAND_SIZE - 1}")
        if index in self.holds:
            self.holds.remove(index)
        else:
            self.holds.add(index)

    def clear_holds(self) -> None:
        self.holds.clear()

    def unheld_indices(self) -> list[int]:
        return [i for i in range(HAND_SIZE) if i not in self.holds]

    def replace_unheld(self, new_cards: Iterable[Card]) -> "Hand":
        """Retorna nova Hand substituindo as posições não-marcadas.

        Preserva a ordem das cartas em HOLD (não rearranja visualmente).
        """
        unheld = self.unheld_indices()
        new_list = list(new_cards)
        if len(new_list) != len(unheld):
            raise ValueError(
                f"recebeu {len(new_list)} cartas, esperava {len(unheld)}"
            )
        cards = list(self.cards)
        for slot, card in zip(unheld, new_list):
            cards[slot] = card
        return Hand(cards=cards, holds=set())

    def __iter__(self):
        return iter(self.cards)

    def __getitem__(self, index: int) -> Card:
        return self.cards[index]

    def __str__(self) -> str:
        return " ".join(str(c) for c in self.cards)
