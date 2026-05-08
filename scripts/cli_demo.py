#!/usr/bin/env python3
"""Smoke test: simula N rodadas e imprime distribuição de combinações.

Executa o motor inteiro (deck + evaluator + paytable) sem UI, gerando
uma sanity check de RNG e detector. Útil para conferir RTP estimado.
"""
from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from videopoker.domain.deck import Deck
from videopoker.domain.evaluator import evaluate
from videopoker.domain.hand import Hand
from videopoker.domain.hand_rank import HandRank
from videopoker.domain.paytable import Paytable


def simulate(n_rounds: int, seed: int | None) -> None:
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    paytable = Paytable()
    counts: Counter[HandRank] = Counter()
    bet = 1.0
    total_bet = 0.0
    total_payout = 0.0

    for _ in range(n_rounds):
        deck = Deck(rng=rng)
        hand = Hand(cards=deck.draw(5))
        # Estratégia "naive": não troca nada — mede distribuição da mão inicial.
        result = evaluate(hand)
        counts[result.rank] += 1
        total_bet += bet
        total_payout += paytable.payout(result, bet)

    print(f"Rodadas simuladas: {n_rounds}")
    print(f"Total apostado:     {total_bet:.2f}")
    print(f"Total pago:         {total_payout:.2f}")
    rtp = (total_payout / total_bet * 100) if total_bet else 0
    print(f"RTP estimado:       {rtp:.2f}%")
    print()
    print(f"{'COMBINAÇÃO':<22}{'OCORRÊNCIAS':>12}{'%':>10}")
    print("-" * 44)
    # Ordena do mais raro ao mais comum (HandRank tem ordem hierárquica).
    for rank in sorted(HandRank, reverse=True):
        c = counts.get(rank, 0)
        pct = c / n_rounds * 100
        print(f"{rank.label:<22}{c:>12}{pct:>9.3f}%")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--rounds", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    simulate(args.rounds, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
