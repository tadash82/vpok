"""Testes da paytable."""
import pytest

from videopoker.domain.evaluator import HandResult
from videopoker.domain.hand_rank import HandRank
from videopoker.domain.paytable import DEFAULT_PAYTABLE, Paytable


def _result(rank: HandRank) -> HandResult:
    return HandResult(rank=rank, kickers=())


def test_default_paytable_values():
    table = Paytable()
    # Calibrados para que aposta = 0.10 produza os "valores de referência"
    # do documento de visão (item 8): 2 PARES paga 0.20 → mult 2x.
    assert table.multiplier_for(HandRank.ROYAL_STRAIGHT) == 500.0
    assert table.multiplier_for(HandRank.STRAIGHT_FLUSH) == 150.0
    assert table.multiplier_for(HandRank.FOUR_OF_A_KIND) == 60.0
    assert table.multiplier_for(HandRank.FULL_HOUSE) == 10.0
    assert table.multiplier_for(HandRank.FLUSH) == 7.0
    assert table.multiplier_for(HandRank.STRAIGHT) == 5.0
    assert table.multiplier_for(HandRank.THREE_OF_A_KIND) == 3.0
    assert table.multiplier_for(HandRank.TWO_PAIR) == 2.0


def test_minimum_bet_produces_doc_reference_values():
    """Aposta de 0.10 deve produzir os prêmios listados no item 8 do doc."""
    table = Paytable()
    bet = 0.10
    assert table.payout(_result(HandRank.TWO_PAIR), bet) == pytest.approx(0.20)
    assert table.payout(_result(HandRank.THREE_OF_A_KIND), bet) == pytest.approx(0.30)
    assert table.payout(_result(HandRank.STRAIGHT), bet) == pytest.approx(0.50)
    assert table.payout(_result(HandRank.FLUSH), bet) == pytest.approx(0.70)
    assert table.payout(_result(HandRank.FULL_HOUSE), bet) == pytest.approx(1.00)
    assert table.payout(_result(HandRank.FOUR_OF_A_KIND), bet) == pytest.approx(6.00)
    assert table.payout(_result(HandRank.STRAIGHT_FLUSH), bet) == pytest.approx(15.00)
    assert table.payout(_result(HandRank.ROYAL_STRAIGHT), bet) == pytest.approx(50.00)


def test_high_card_pays_zero():
    table = Paytable()
    assert table.multiplier_for(HandRank.HIGH_CARD) == 0.0
    assert table.payout(_result(HandRank.HIGH_CARD), bet=10) == 0.0


def test_payout_uses_bet():
    table = Paytable()
    assert table.payout(_result(HandRank.ROYAL_STRAIGHT), bet=0.20) == pytest.approx(100.0)
    assert table.payout(_result(HandRank.FLUSH), bet=1.0) == pytest.approx(7.0)


def test_paytable_iterable_in_descending_value():
    """A paytable é iterável e exibe combinações da maior para a menor."""
    multipliers = [e.multiplier for e in DEFAULT_PAYTABLE]
    assert multipliers == sorted(multipliers, reverse=True)


def test_custom_paytable():
    from videopoker.domain.paytable import PayoutEntry

    custom = (
        PayoutEntry(HandRank.ROYAL_STRAIGHT, 100.0, "ROYAL"),
        PayoutEntry(HandRank.FLUSH, 1.0, "FLUSH"),
    )
    table = Paytable(entries=custom)
    assert table.multiplier_for(HandRank.ROYAL_STRAIGHT) == 100.0
    assert table.multiplier_for(HandRank.STRAIGHT_FLUSH) == 0.0  # não tem entrada
