"""Testes do avaliador de mãos.

Cobertura por mão canônica de cada combinação implementada, incluindo
edge cases (wheel A-2-3-4-5, Royal vs Straight Flush, etc.).
"""
from videopoker.domain.card import Card, Rank, Suit
from videopoker.domain.evaluator import evaluate
from videopoker.domain.hand import Hand
from videopoker.domain.hand_rank import HandRank


def hand_of(*cards: tuple[Rank, Suit]) -> Hand:
    return Hand(cards=[Card(r, s) for r, s in cards])


# ---- Royal Straight ----

def test_royal_straight():
    h = hand_of(
        (Rank.TEN, Suit.HEARTS),
        (Rank.JACK, Suit.HEARTS),
        (Rank.QUEEN, Suit.HEARTS),
        (Rank.KING, Suit.HEARTS),
        (Rank.ACE, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.ROYAL_STRAIGHT


def test_royal_straight_unordered_cards():
    h = hand_of(
        (Rank.ACE, Suit.SPADES),
        (Rank.TEN, Suit.SPADES),
        (Rank.KING, Suit.SPADES),
        (Rank.JACK, Suit.SPADES),
        (Rank.QUEEN, Suit.SPADES),
    )
    assert evaluate(h).rank is HandRank.ROYAL_STRAIGHT


# ---- Straight Flush ----

def test_straight_flush_low():
    h = hand_of(
        (Rank.FIVE, Suit.CLUBS),
        (Rank.SIX, Suit.CLUBS),
        (Rank.SEVEN, Suit.CLUBS),
        (Rank.EIGHT, Suit.CLUBS),
        (Rank.NINE, Suit.CLUBS),
    )
    assert evaluate(h).rank is HandRank.STRAIGHT_FLUSH


def test_straight_flush_wheel():
    """A-2-3-4-5 mesmo naipe é Straight Flush, não Royal."""
    h = hand_of(
        (Rank.ACE, Suit.DIAMONDS),
        (Rank.TWO, Suit.DIAMONDS),
        (Rank.THREE, Suit.DIAMONDS),
        (Rank.FOUR, Suit.DIAMONDS),
        (Rank.FIVE, Suit.DIAMONDS),
    )
    assert evaluate(h).rank is HandRank.STRAIGHT_FLUSH


def test_straight_flush_just_below_royal():
    h = hand_of(
        (Rank.NINE, Suit.HEARTS),
        (Rank.TEN, Suit.HEARTS),
        (Rank.JACK, Suit.HEARTS),
        (Rank.QUEEN, Suit.HEARTS),
        (Rank.KING, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.STRAIGHT_FLUSH


# ---- Quadra ----

def test_four_of_a_kind():
    h = hand_of(
        (Rank.SEVEN, Suit.HEARTS),
        (Rank.SEVEN, Suit.CLUBS),
        (Rank.SEVEN, Suit.DIAMONDS),
        (Rank.SEVEN, Suit.SPADES),
        (Rank.TWO, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.FOUR_OF_A_KIND


# ---- Full House ----

def test_full_house():
    h = hand_of(
        (Rank.KING, Suit.HEARTS),
        (Rank.KING, Suit.CLUBS),
        (Rank.KING, Suit.DIAMONDS),
        (Rank.FIVE, Suit.SPADES),
        (Rank.FIVE, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.FULL_HOUSE


# ---- Flush ----

def test_flush():
    h = hand_of(
        (Rank.TWO, Suit.SPADES),
        (Rank.FIVE, Suit.SPADES),
        (Rank.NINE, Suit.SPADES),
        (Rank.JACK, Suit.SPADES),
        (Rank.KING, Suit.SPADES),
    )
    assert evaluate(h).rank is HandRank.FLUSH


def test_flush_does_not_match_when_almost_straight():
    """Flush sem ser sequencial."""
    h = hand_of(
        (Rank.TWO, Suit.HEARTS),
        (Rank.FOUR, Suit.HEARTS),
        (Rank.SIX, Suit.HEARTS),
        (Rank.EIGHT, Suit.HEARTS),
        (Rank.TEN, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.FLUSH


# ---- Straight ----

def test_straight_ace_high():
    h = hand_of(
        (Rank.TEN, Suit.HEARTS),
        (Rank.JACK, Suit.CLUBS),
        (Rank.QUEEN, Suit.DIAMONDS),
        (Rank.KING, Suit.SPADES),
        (Rank.ACE, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.STRAIGHT


def test_straight_wheel_ace_low():
    """A-2-3-4-5 conta como straight com 5 alto."""
    h = hand_of(
        (Rank.ACE, Suit.HEARTS),
        (Rank.TWO, Suit.CLUBS),
        (Rank.THREE, Suit.DIAMONDS),
        (Rank.FOUR, Suit.SPADES),
        (Rank.FIVE, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.STRAIGHT


def test_straight_middle():
    h = hand_of(
        (Rank.FOUR, Suit.HEARTS),
        (Rank.FIVE, Suit.CLUBS),
        (Rank.SIX, Suit.DIAMONDS),
        (Rank.SEVEN, Suit.SPADES),
        (Rank.EIGHT, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.STRAIGHT


def test_not_a_straight_with_gap():
    h = hand_of(
        (Rank.FOUR, Suit.HEARTS),
        (Rank.FIVE, Suit.CLUBS),
        (Rank.SIX, Suit.DIAMONDS),
        (Rank.SEVEN, Suit.SPADES),
        (Rank.NINE, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.HIGH_CARD


def test_not_a_straight_qkqa_2():
    """Q-K-A-2-3 não é straight (não dá volta)."""
    h = hand_of(
        (Rank.QUEEN, Suit.HEARTS),
        (Rank.KING, Suit.CLUBS),
        (Rank.ACE, Suit.DIAMONDS),
        (Rank.TWO, Suit.SPADES),
        (Rank.THREE, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.HIGH_CARD


# ---- Trinca ----

def test_three_of_a_kind():
    h = hand_of(
        (Rank.NINE, Suit.HEARTS),
        (Rank.NINE, Suit.CLUBS),
        (Rank.NINE, Suit.DIAMONDS),
        (Rank.TWO, Suit.SPADES),
        (Rank.SEVEN, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.THREE_OF_A_KIND


# ---- Dois Pares ----

def test_two_pair():
    h = hand_of(
        (Rank.JACK, Suit.HEARTS),
        (Rank.JACK, Suit.CLUBS),
        (Rank.FOUR, Suit.DIAMONDS),
        (Rank.FOUR, Suit.SPADES),
        (Rank.SEVEN, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.TWO_PAIR


# ---- High Card (não premiado) ----

def test_high_card():
    h = hand_of(
        (Rank.TWO, Suit.HEARTS),
        (Rank.FIVE, Suit.CLUBS),
        (Rank.SEVEN, Suit.DIAMONDS),
        (Rank.NINE, Suit.SPADES),
        (Rank.KING, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.HIGH_CARD


def test_one_pair_returns_high_card():
    """Um par só não é combinação premiada (não está na paytable)."""
    h = hand_of(
        (Rank.TEN, Suit.HEARTS),
        (Rank.TEN, Suit.CLUBS),
        (Rank.SEVEN, Suit.DIAMONDS),
        (Rank.NINE, Suit.SPADES),
        (Rank.KING, Suit.HEARTS),
    )
    assert evaluate(h).rank is HandRank.HIGH_CARD


# ---- Resultado: precedência ----

def test_full_house_beats_three_of_a_kind_detection():
    """Se for full house, não pode classificar como trinca."""
    h = hand_of(
        (Rank.KING, Suit.HEARTS),
        (Rank.KING, Suit.CLUBS),
        (Rank.KING, Suit.DIAMONDS),
        (Rank.FIVE, Suit.SPADES),
        (Rank.FIVE, Suit.HEARTS),
    )
    result = evaluate(h)
    assert result.rank is HandRank.FULL_HOUSE
    assert result.rank is not HandRank.THREE_OF_A_KIND


def test_kickers_ordered_by_frequency_then_value():
    h = hand_of(
        (Rank.KING, Suit.HEARTS),
        (Rank.KING, Suit.CLUBS),
        (Rank.KING, Suit.DIAMONDS),
        (Rank.FIVE, Suit.SPADES),
        (Rank.FIVE, Suit.HEARTS),
    )
    result = evaluate(h)
    assert result.kickers[0] is Rank.KING
    assert result.kickers[1] is Rank.FIVE
