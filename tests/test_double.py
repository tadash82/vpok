"""Testes da regra de dobra (Double Up)."""
from __future__ import annotations

import random

import pytest

from videopoker.domain.card import Card, Rank, Suit
from videopoker.domain.deck import Deck
from videopoker.domain.evaluator import HandResult
from videopoker.domain.hand import Hand
from videopoker.domain.hand_rank import HandRank
from videopoker.game.session import (
    DoubleOutcome,
    GameSession,
    InvalidBetError,
)
from videopoker.game.state import GameState, InvalidTransitionError


def _force_winning_round(s: GameSession) -> None:
    """Força a sessão para um estado EVALUATED com pending_prize > 0.

    Acessa atributos privados — aceitável apenas em testes.
    """
    s.set_bet(1)
    s.deal()
    # Substitui a mão por uma vitória conhecida (FULL HOUSE).
    s._hand = Hand(
        cards=[
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.KING, Suit.CLUBS),
            Card(Rank.KING, Suit.DIAMONDS),
            Card(Rank.FIVE, Suit.SPADES),
            Card(Rank.FIVE, Suit.HEARTS),
        ]
    )
    # Marca todas como hold para draw() não trocar.
    for i in range(5):
        s._hand.toggle_hold(i)
    s.draw()


class _StubDeck(Deck):
    """Deck que devolve cartas pré-definidas em ordem."""

    def __init__(self, cards: list[Card]) -> None:
        super().__init__(rng=random.Random(0))
        self._cards = list(cards)


def test_pending_prize_after_winning_round():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    assert s.state is GameState.EVALUATED
    # FULL HOUSE × 1 (aposta) = 10.0 (multiplicador atual)
    assert s.pending_prize == 10.0
    # Crédito ainda NÃO foi creditado (em pending até take_prize).
    assert s.credits == 9.0  # 10 - aposta(1)


def test_take_prize_after_evaluated_credits_pending():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    assert s.pending_prize == 10.0
    s.take_prize()
    assert s.state is GameState.IDLE
    assert s.credits == 19.0  # 9 (pós-aposta) + 10 (FULL HOUSE)
    assert s.pending_prize == 0.0


def test_double_win_doubles_pending():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    initial_pending = s.pending_prize
    # Forca a próxima carta do baralho para ser ALTA (>7).
    s._deck._cards = [Card(Rank.KING, Suit.SPADES)] + list(s._deck._cards)

    s.start_double()
    assert s.state is GameState.DOUBLE_OFFERED
    assert s.double_card == Card(Rank.KING, Suit.SPADES)

    outcome = s.guess_big()
    assert outcome is DoubleOutcome.WIN
    assert s.pending_prize == initial_pending * 2
    assert s.state is GameState.DOUBLE_REVEALED


def test_double_lose_zeros_pending():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    s._deck._cards = [Card(Rank.KING, Suit.SPADES)] + list(s._deck._cards)

    s.start_double()
    outcome = s.guess_mini()  # apostou MINI mas saiu K (BIG) → erro
    assert outcome is DoubleOutcome.LOSE
    assert s.pending_prize == 0.0


def test_double_tie_keeps_pending():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    pending = s.pending_prize
    s._deck._cards = [Card(Rank.SEVEN, Suit.HEARTS)] + list(s._deck._cards)

    s.start_double()
    outcome = s.guess_big()  # qualquer aposta empata em 7
    assert outcome is DoubleOutcome.TIE
    assert s.pending_prize == pending


def test_continue_after_tie_draws_new_card():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    s._deck._cards = [
        Card(Rank.SEVEN, Suit.HEARTS),  # primeira: empate
        Card(Rank.TWO, Suit.CLUBS),     # segunda: BIG erra, MINI acerta
    ] + list(s._deck._cards)

    s.start_double()
    s.guess_big()  # empate
    s.continue_after_reveal()
    assert s.state is GameState.DOUBLE_OFFERED
    assert s.double_card == Card(Rank.TWO, Suit.CLUBS)


def test_continue_after_lose_goes_to_idle():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    s._deck._cards = [Card(Rank.KING, Suit.SPADES)] + list(s._deck._cards)

    s.start_double()
    s.guess_mini()  # erro
    s.continue_after_reveal()
    assert s.state is GameState.IDLE
    # Crédito não foi acrescido (perdeu o pending).
    assert s.credits == 9.0  # 10 - aposta(1) original


def test_continue_after_win_lets_double_again():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    s._deck._cards = [
        Card(Rank.KING, Suit.SPADES),
        Card(Rank.QUEEN, Suit.HEARTS),
    ] + list(s._deck._cards)

    s.start_double()
    s.guess_big()
    pending_after_win = s.pending_prize
    assert pending_after_win == 20.0  # FULL HOUSE 10 dobrou para 20
    s.continue_after_reveal()
    assert s.state is GameState.DOUBLE_OFFERED
    assert s.double_card == Card(Rank.QUEEN, Suit.HEARTS)


def test_take_prize_during_double_offered():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    s._deck._cards = [Card(Rank.KING, Suit.SPADES)] + list(s._deck._cards)

    s.start_double()
    s.guess_big()
    # Após win, pending = 20 (FULL HOUSE 10 dobrado). Jogador decide levar.
    s.take_prize()
    assert s.state is GameState.IDLE
    assert s.credits == 9.0 + 20.0  # crédito pós-aposta + pending dobrado


def test_double_history_records_revealed_cards():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    cards = [
        Card(Rank.KING, Suit.SPADES),
        Card(Rank.QUEEN, Suit.HEARTS),
        Card(Rank.SEVEN, Suit.DIAMONDS),
    ]
    s._deck._cards = cards + list(s._deck._cards)

    s.start_double()
    s.guess_big()
    s.continue_after_reveal()
    s.guess_big()
    s.continue_after_reveal()
    s.guess_big()  # 7 → empate

    assert s.double_history == cards


def test_pivot_card_seven_is_tie_regardless_of_guess():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    s._deck._cards = [Card(Rank.SEVEN, Suit.CLUBS)] + list(s._deck._cards)
    s.start_double()
    assert s.guess_mini() is DoubleOutcome.TIE


def test_card_value_below_pivot_mini_wins():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    s._deck._cards = [Card(Rank.TWO, Suit.CLUBS)] + list(s._deck._cards)
    s.start_double()
    assert s.guess_mini() is DoubleOutcome.WIN


def test_card_value_above_pivot_big_wins():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    s._deck._cards = [Card(Rank.JACK, Suit.CLUBS)] + list(s._deck._cards)
    s.start_double()
    assert s.guess_big() is DoubleOutcome.WIN


def test_cannot_start_double_without_pending_prize():
    """Se a rodada não foi premiada, não pode dobrar (pending=0)."""
    s = GameSession(initial_credits=10, rng=random.Random(123))
    s.set_bet(1)
    s.deal()
    # Sem trocar nada — provavelmente não-premiada com seed=123.
    s.draw()
    if s.pending_prize == 0:
        with pytest.raises(InvalidTransitionError):
            s.start_double()


def test_deck_exhaustion_forces_take_prize():
    """Se o baralho esgotar, start_double força take_prize automaticamente."""
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    # Esvazia o deck restante.
    s._deck._cards = []

    s.start_double()
    assert s.state is GameState.IDLE
    # 9 (pós-aposta) + 10 (FULL HOUSE) = 19
    assert s.credits == 19.0


def test_cannot_guess_outside_double_offered():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    with pytest.raises(InvalidTransitionError):
        s.guess_big()


def test_cannot_continue_outside_double_revealed():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    with pytest.raises(InvalidTransitionError):
        s.continue_after_reveal()


def test_poker_final_hand_persists_during_double():
    """A mão de poker premiada permanece visível durante a fase de dobra."""
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    snapshot = list(s.poker_final_hand)
    s._deck._cards = [Card(Rank.KING, Suit.SPADES)] + list(s._deck._cards)
    s.start_double()
    assert list(s.poker_final_hand) == snapshot


def test_take_prize_resets_double_state():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    s._deck._cards = [
        Card(Rank.KING, Suit.SPADES),
        Card(Rank.QUEEN, Suit.HEARTS),
    ] + list(s._deck._cards)
    s.start_double()
    s.guess_big()
    s.take_prize()
    assert s.double_card is None
    assert s.double_history == []
    assert s.poker_final_hand is None


def test_chained_doubles_accumulate():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    initial = s.pending_prize  # 1.0
    s._deck._cards = [
        Card(Rank.KING, Suit.SPADES),
        Card(Rank.QUEEN, Suit.HEARTS),
        Card(Rank.JACK, Suit.DIAMONDS),
    ] + list(s._deck._cards)

    for _ in range(3):
        s.start_double() if s.state is GameState.EVALUATED else s.continue_after_reveal()
        s.guess_big()
    assert s.pending_prize == initial * 8  # 1 → 2 → 4 → 8


# ---------- Aposta cheia (rank + naipe) ----------

def test_guess_exact_full_match_pays_10x():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    initial = s.pending_prize
    s._deck._cards = [Card(Rank.QUEEN, Suit.HEARTS)] + list(s._deck._cards)
    s.start_double()
    outcome = s.guess_exact(Rank.QUEEN, Suit.HEARTS)
    assert outcome is DoubleOutcome.WIN
    assert s.pending_prize == initial * 10
    assert s.last_double_multiplier == 10


def test_guess_exact_rank_only_pays_5x():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    initial = s.pending_prize
    s._deck._cards = [Card(Rank.QUEEN, Suit.HEARTS)] + list(s._deck._cards)
    s.start_double()
    outcome = s.guess_exact(Rank.QUEEN, Suit.SPADES)  # rank certo, naipe errado
    assert outcome is DoubleOutcome.WIN
    assert s.pending_prize == initial * 5
    assert s.last_double_multiplier == 5


def test_guess_exact_wrong_rank_loses():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    s._deck._cards = [Card(Rank.QUEEN, Suit.HEARTS)] + list(s._deck._cards)
    s.start_double()
    outcome = s.guess_exact(Rank.KING, Suit.HEARTS)  # naipe certo, rank errado
    assert outcome is DoubleOutcome.LOSE
    assert s.pending_prize == 0.0
    assert s.last_double_multiplier == 0


def test_guess_exact_no_tie_on_seven():
    """Pivô 7 só se aplica a BIG/MINI; em CHEIO, não há empate."""
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    s._deck._cards = [Card(Rank.SEVEN, Suit.HEARTS)] + list(s._deck._cards)
    s.start_double()
    outcome = s.guess_exact(Rank.SEVEN, Suit.HEARTS)  # acerta cheio
    assert outcome is DoubleOutcome.WIN


def test_guess_exact_after_win_can_continue_doubling():
    """Acertar a aposta cheia permite continuar dobrando (BIG/MINI ou cheio de novo)."""
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    s._deck._cards = [
        Card(Rank.QUEEN, Suit.HEARTS),
        Card(Rank.KING, Suit.SPADES),
    ] + list(s._deck._cards)
    s.start_double()
    s.guess_exact(Rank.QUEEN, Suit.HEARTS)  # 10x
    s.continue_after_reveal()
    assert s.state is GameState.DOUBLE_OFFERED
    s.guess_big()  # K → big OK
    assert s.last_double_multiplier == 2


def test_guess_exact_outside_double_offered_raises():
    s = GameSession(initial_credits=10, rng=random.Random(7))
    with pytest.raises(InvalidTransitionError):
        s.guess_exact(Rank.SEVEN, Suit.HEARTS)


def test_chained_exact_wins_compound():
    """Dois acertos em cheio seguidos: 1 → 10 → 100."""
    s = GameSession(initial_credits=10, rng=random.Random(7))
    _force_winning_round(s)
    initial = s.pending_prize
    s._deck._cards = [
        Card(Rank.QUEEN, Suit.HEARTS),
        Card(Rank.KING, Suit.SPADES),
    ] + list(s._deck._cards)
    s.start_double()
    s.guess_exact(Rank.QUEEN, Suit.HEARTS)
    s.continue_after_reveal()
    s.guess_exact(Rank.KING, Suit.SPADES)
    assert s.pending_prize == initial * 100
