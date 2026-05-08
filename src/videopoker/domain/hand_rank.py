"""Hierarquia de combinações de poker reconhecidas pelo avaliador."""
from __future__ import annotations

from enum import IntEnum


class HandRank(IntEnum):
    """Combinações válidas, ordenadas do menor para o maior valor.

    Quanto maior o valor, mais raro/valioso. A ordem aqui é a referência
    canônica usada pelo avaliador e pela paytable.

    Os pontos de extensão "A DEFINIR" do documento (VEGAS ROYAL, FIGURAS)
    serão inseridos respeitando essa ordem quando suas regras forem
    finalizadas.
    """

    HIGH_CARD = 0
    TWO_PAIR = 1
    THREE_OF_A_KIND = 2
    STRAIGHT = 3
    FLUSH = 4
    FULL_HOUSE = 5
    FOUR_OF_A_KIND = 6
    STRAIGHT_FLUSH = 7
    ROYAL_STRAIGHT = 8

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS: dict[HandRank, str] = {
    HandRank.HIGH_CARD: "CARTA ALTA",
    HandRank.TWO_PAIR: "2 PARES",
    HandRank.THREE_OF_A_KIND: "TRINCA",
    HandRank.STRAIGHT: "STRAIGHT",
    HandRank.FLUSH: "FLUSH",
    HandRank.FULL_HOUSE: "FULL HOUSE",
    HandRank.FOUR_OF_A_KIND: "QUADRA",
    HandRank.STRAIGHT_FLUSH: "STRAIGHT FLUSH",
    HandRank.ROYAL_STRAIGHT: "ROYAL STRAIGHT",
}
