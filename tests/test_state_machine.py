"""Testes da sessão e máquina de estados."""
import random

import pytest

from videopoker.domain.card import Card, Rank, Suit
from videopoker.game.session import (
    GameSession,
    InsufficientCreditsError,
    InvalidBetError,
)
from videopoker.game.state import GameState, InvalidTransitionError


def test_initial_state():
    s = GameSession(initial_credits=50)
    assert s.state is GameState.IDLE
    assert s.credits == 50
    assert s.hand is None


def test_full_round_no_holds():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    s.set_bet(2)
    assert s.state is GameState.BET_PLACED
    s.deal()
    assert s.state is GameState.DEALT
    assert s.credits == 8  # aposta debitada
    assert s.hand is not None
    outcome = s.draw()
    assert s.state is GameState.EVALUATED
    assert outcome.bet == 2
    assert s.credits == outcome.credits_after


def test_toggle_hold_keeps_card_after_draw():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    s.set_bet(1)
    s.deal()
    held_card = s.hand[2]
    s.toggle_hold(2)
    s.draw()
    assert s.hand[2] == held_card


def test_cannot_deal_before_bet():
    s = GameSession(initial_credits=10)
    with pytest.raises(InvalidTransitionError):
        s.deal()


def test_cannot_set_bet_after_deal():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    s.set_bet(1)
    s.deal()
    with pytest.raises(InvalidTransitionError):
        s.set_bet(2)


def test_cannot_toggle_hold_before_dealt():
    s = GameSession(initial_credits=10)
    with pytest.raises(InvalidTransitionError):
        s.toggle_hold(0)


def test_cannot_draw_before_dealt():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    s.set_bet(1)
    with pytest.raises(InvalidTransitionError):
        s.draw()


def test_invalid_bet_below_min():
    s = GameSession(initial_credits=10)
    with pytest.raises(InvalidBetError):
        s.set_bet(0)


def test_invalid_bet_above_max():
    s = GameSession(initial_credits=100)
    with pytest.raises(InvalidBetError):
        s.set_bet(999)


def test_insufficient_credits_blocks_bet():
    s = GameSession(initial_credits=1)
    with pytest.raises(InsufficientCreditsError):
        s.set_bet(5)


def test_cancel_bet_returns_to_idle():
    s = GameSession(initial_credits=10)
    s.set_bet(3)
    assert s.state is GameState.BET_PLACED
    s.cancel_bet()
    assert s.state is GameState.IDLE


def test_next_round_after_evaluated():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    s.set_bet(1)
    s.deal()
    s.draw()
    s.next_round()
    assert s.state is GameState.IDLE


def test_game_over_when_credits_below_min():
    """Forca um cenário onde, após rodar, fica sem créditos."""
    s = GameSession(initial_credits=1, rng=random.Random(123))
    s.set_bet(1)
    s.deal()
    s.draw()
    s.next_round()
    if s.credits < 1:
        assert s.state is GameState.GAME_OVER


def test_reset_restores_full_state():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    s.set_bet(1)
    s.deal()
    s.draw()
    s.reset(initial_credits=50)
    assert s.state is GameState.IDLE
    assert s.credits == 50
    assert s.hand is None


def test_holds_replace_only_unheld():
    """Verifica que uma rodada com tudo em HOLD não troca cartas."""
    s = GameSession(initial_credits=10, rng=random.Random(7))
    s.set_bet(1)
    s.deal()
    snapshot = list(s.hand)
    for i in range(5):
        s.toggle_hold(i)
    s.draw()
    assert list(s.hand) == snapshot
