"""Testes da modelagem de cartas."""
from videopoker.domain.card import Card, Rank, Suit


def test_rank_ordering():
    assert Rank.TWO < Rank.ACE
    assert Rank.JACK < Rank.QUEEN < Rank.KING < Rank.ACE
    assert Rank.TEN.value_int == 10


def test_card_is_hashable_and_frozen():
    a = Card(Rank.ACE, Suit.SPADES)
    b = Card(Rank.ACE, Suit.SPADES)
    c = Card(Rank.ACE, Suit.HEARTS)
    assert a == b
    assert a != c
    assert {a, b, c} == {a, c}


def test_card_str_and_repr():
    card = Card(Rank.KING, Suit.DIAMONDS)
    assert str(card) == "K♦"
    assert "KING" in repr(card)
    assert "DIAMONDS" in repr(card)


def test_suit_color():
    assert Suit.HEARTS.color == "vermelho"
    assert Suit.DIAMONDS.color == "vermelho"
    assert Suit.CLUBS.color == "preto"
    assert Suit.SPADES.color == "preto"
