"""Avaliador de mãos de Five-Card Draw.

Implementa o algoritmo via lista ordenada de detectores: o primeiro que
casar com a mão vence. A ordem segue a hierarquia de HandRank (do mais raro
ao mais comum).

Pontos de extensão para regras "A DEFINIR" do documento:
- VEGAS ROYAL: novo detector inserido no topo de DETECTORS.
- FIGURAS: detector inserido entre QUADRA e FULL HOUSE.

As regras especiais (Maior/Menor que 7, Cheia, etc.) NÃO são detectores
de poker — vivem em domain/rules/extra.py como camada à parte.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Callable

from .card import Rank
from .hand import Hand
from .hand_rank import HandRank


@dataclass(frozen=True)
class HandFeatures:
    """Estruturas pré-computadas usadas pelos detectores."""

    rank_counts: Counter
    is_flush: bool
    is_straight: bool
    straight_high: Rank | None  # Rank mais alto da sequência (None se não for straight)


@dataclass(frozen=True)
class HandResult:
    rank: HandRank
    kickers: tuple[Rank, ...]

    @property
    def label(self) -> str:
        return self.rank.label


def _compute_features(hand: Hand) -> HandFeatures:
    ranks = [c.rank for c in hand]
    suits = [c.suit for c in hand]
    rank_counts = Counter(ranks)

    is_flush = len(set(suits)) == 1

    # Straight: cinco valores consecutivos OU caso especial A-2-3-4-5 (wheel).
    rank_values = sorted(r.value_int for r in ranks)
    is_straight = False
    straight_high: Rank | None = None
    if len(set(rank_values)) == 5:
        if rank_values[-1] - rank_values[0] == 4:
            is_straight = True
            straight_high = max(ranks)
        elif rank_values == [2, 3, 4, 5, 14]:
            # Wheel (A-low): topo da sequência é o 5.
            is_straight = True
            straight_high = Rank.FIVE

    return HandFeatures(
        rank_counts=rank_counts,
        is_flush=is_flush,
        is_straight=is_straight,
        straight_high=straight_high,
    )


def _is_royal_straight(features: HandFeatures) -> bool:
    return (
        features.is_flush
        and features.is_straight
        and features.straight_high is Rank.ACE
    )


def _is_straight_flush(features: HandFeatures) -> bool:
    return features.is_flush and features.is_straight


def _is_four_of_a_kind(features: HandFeatures) -> bool:
    return 4 in features.rank_counts.values()


def _is_full_house(features: HandFeatures) -> bool:
    counts = sorted(features.rank_counts.values(), reverse=True)
    return counts == [3, 2]


def _is_flush(features: HandFeatures) -> bool:
    return features.is_flush


def _is_straight(features: HandFeatures) -> bool:
    return features.is_straight


def _is_three_of_a_kind(features: HandFeatures) -> bool:
    return 3 in features.rank_counts.values()


def _is_two_pair(features: HandFeatures) -> bool:
    pair_count = sum(1 for c in features.rank_counts.values() if c == 2)
    return pair_count == 2


# Lista ordenada (mais raro → mais comum). Primeiro que casar vence.
# Para incluir VEGAS ROYAL/FIGURAS no futuro, basta inserir aqui.
DETECTORS: list[tuple[HandRank, Callable[[HandFeatures], bool]]] = [
    (HandRank.ROYAL_STRAIGHT, _is_royal_straight),
    (HandRank.STRAIGHT_FLUSH, _is_straight_flush),
    (HandRank.FOUR_OF_A_KIND, _is_four_of_a_kind),
    (HandRank.FULL_HOUSE, _is_full_house),
    (HandRank.FLUSH, _is_flush),
    (HandRank.STRAIGHT, _is_straight),
    (HandRank.THREE_OF_A_KIND, _is_three_of_a_kind),
    (HandRank.TWO_PAIR, _is_two_pair),
]


def _kickers_for(features: HandFeatures) -> tuple[Rank, ...]:
    """Ordena os ranks por (frequência desc, valor desc) — útil para desempates."""
    items = sorted(
        features.rank_counts.items(),
        key=lambda kv: (kv[1], kv[0].value_int),
        reverse=True,
    )
    return tuple(rank for rank, _ in items)


def evaluate(hand: Hand) -> HandResult:
    """Avalia uma mão de 5 cartas e retorna a maior combinação detectada."""
    features = _compute_features(hand)
    kickers = _kickers_for(features)
    for hand_rank, detector in DETECTORS:
        if detector(features):
            return HandResult(rank=hand_rank, kickers=kickers)
    return HandResult(rank=HandRank.HIGH_CARD, kickers=kickers)
