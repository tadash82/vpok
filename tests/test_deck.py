"""Testes do baralho."""
import random

import pytest

from videopoker.domain.deck import Deck, EmptyDeckError


def test_deck_has_52_unique_cards():
    deck = Deck(rng=random.Random(42))
    cards = list(deck.peek())
    assert len(cards) == 52
    assert len(set(cards)) == 52


def test_draw_removes_cards():
    deck = Deck(rng=random.Random(42))
    drawn = deck.draw(5)
    assert len(drawn) == 5
    assert deck.remaining == 47


def test_drawn_cards_are_not_in_deck():
    deck = Deck(rng=random.Random(42))
    drawn = deck.draw(10)
    remaining = list(deck.peek())
    assert set(drawn).isdisjoint(set(remaining))


def test_seeded_decks_are_deterministic():
    deck_a = Deck(rng=random.Random(1234))
    deck_b = Deck(rng=random.Random(1234))
    assert deck_a.draw(52) == deck_b.draw(52)


def test_draw_more_than_remaining_raises():
    deck = Deck(rng=random.Random(42))
    deck.draw(50)
    with pytest.raises(EmptyDeckError):
        deck.draw(5)


def test_draw_negative_raises():
    deck = Deck(rng=random.Random(42))
    with pytest.raises(ValueError):
        deck.draw(-1)


def test_default_rng_is_systemrandom():
    deck = Deck()
    assert deck.remaining == 52
