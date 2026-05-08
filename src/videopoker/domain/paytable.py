"""Tabela de pagamentos (paytable) do Video Poker."""
from __future__ import annotations

from dataclasses import dataclass

from .evaluator import HandResult
from .hand_rank import HandRank


@dataclass(frozen=True)
class PayoutEntry:
    rank: HandRank
    multiplier: float
    label: str


# Multiplicadores: aposta × multiplicador = prêmio.
# Calibrados para que aposta = 0.10 produza os "valores de referência"
# do item 8 do documento de visão (ex.: 2 PARES paga 0.20 → mult 2x).
# Valores "A DEFINIR" (VEGAS ROYAL, FIGURAS) ficam fora até a spec
# definir suas regras. Adicionar é incluir entrada aqui + detector
# em evaluator.DETECTORS.
DEFAULT_PAYTABLE: tuple[PayoutEntry, ...] = (
    PayoutEntry(HandRank.ROYAL_STRAIGHT, 500.0, "ROYAL STRAIGHT"),
    PayoutEntry(HandRank.STRAIGHT_FLUSH, 150.0, "STRAIGHT FLUSH"),
    PayoutEntry(HandRank.FOUR_OF_A_KIND, 60.0, "QUADRA"),
    PayoutEntry(HandRank.FULL_HOUSE, 10.0, "FULL HOUSE"),
    PayoutEntry(HandRank.FLUSH, 7.0, "FLUSH"),
    PayoutEntry(HandRank.STRAIGHT, 5.0, "STRAIGHT"),
    PayoutEntry(HandRank.THREE_OF_A_KIND, 3.0, "TRINCA"),
    PayoutEntry(HandRank.TWO_PAIR, 2.0, "2 PARES"),
)


class Paytable:
    def __init__(self, entries: tuple[PayoutEntry, ...] = DEFAULT_PAYTABLE) -> None:
        self.entries = entries
        self._by_rank: dict[HandRank, PayoutEntry] = {e.rank: e for e in entries}

    def multiplier_for(self, rank: HandRank) -> float:
        entry = self._by_rank.get(rank)
        return entry.multiplier if entry is not None else 0.0

    def payout(self, result: HandResult, bet: float) -> float:
        """Calcula prêmio: aposta × multiplicador da combinação.

        Mãos sem entrada na paytable (HIGH_CARD, etc.) pagam 0.
        """
        return bet * self.multiplier_for(result.rank)

    def __iter__(self):
        return iter(self.entries)
