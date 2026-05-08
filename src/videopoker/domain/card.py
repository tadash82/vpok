"""Modelagem de cartas: Suit, Rank e Card."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Suit(Enum):
    HEARTS = ("♥", "vermelho")
    DIAMONDS = ("♦", "vermelho")
    CLUBS = ("♣", "preto")
    SPADES = ("♠", "preto")

    @property
    def symbol(self) -> str:
        return self.value[0]

    @property
    def color(self) -> str:
        return self.value[1]


class Rank(Enum):
    TWO = (2, "2")
    THREE = (3, "3")
    FOUR = (4, "4")
    FIVE = (5, "5")
    SIX = (6, "6")
    SEVEN = (7, "7")
    EIGHT = (8, "8")
    NINE = (9, "9")
    TEN = (10, "10")
    JACK = (11, "J")
    QUEEN = (12, "Q")
    KING = (13, "K")
    ACE = (14, "A")

    @property
    def value_int(self) -> int:
        return self.value[0]

    @property
    def label(self) -> str:
        return self.value[1]

    def __lt__(self, other: "Rank") -> bool:
        return self.value_int < other.value_int


@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        return f"{self.rank.label}{self.suit.symbol}"

    def __repr__(self) -> str:
        return f"Card({self.rank.name}, {self.suit.name})"
