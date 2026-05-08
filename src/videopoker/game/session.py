"""Sessão de jogo: créditos, aposta corrente e fluxo de uma rodada."""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from ..config import DEFAULT_BET, HAND_SIZE, INITIAL_CREDITS, MAX_BET, MIN_BET
from ..domain.card import Card, Rank, Suit
from ..domain.deck import Deck
from ..domain.evaluator import HandResult, evaluate
from ..domain.hand import Hand
from ..domain.paytable import Paytable
from .state import GameState, InvalidTransitionError


class InsufficientCreditsError(RuntimeError):
    pass


class InvalidBetError(ValueError):
    pass


class DoubleOutcome(Enum):
    WIN = "win"
    TIE = "tie"
    LOSE = "lose"


# Pivô da dobra: cartas com valor > PIVOT são "big", < PIVOT são "mini",
# == PIVOT empata.
DOUBLE_PIVOT = 7

# Multiplicadores aplicados ao prêmio em cada modalidade de acerto.
DOUBLE_MULTIPLIER_BIG_MINI = 2
DOUBLE_MULTIPLIER_EXACT_RANK = 5
DOUBLE_MULTIPLIER_EXACT_FULL = 10


@dataclass
class RoundOutcome:
    """Resumo do que aconteceu em uma rodada de poker (para a UI exibir)."""

    final_hand: Hand
    result: HandResult
    bet: float
    payout: float
    credits_after: float

    @property
    def won(self) -> bool:
        return self.payout > 0


class GameSession:
    """Orquestra o fluxo de uma rodada e gerencia créditos.

    Após uma rodada de poker premiada, o prêmio fica em "pending" — em risco
    durante a fase de DOBRA. O crédito só é incrementado quando o jogador
    aciona take_prize() (ou perde por errar a dobra, caso em que pending=0).

    A UI chama métodos públicos. A sessão valida o estado atual e levanta
    InvalidTransitionError se a operação não for permitida agora.
    """

    def __init__(
        self,
        initial_credits: float = INITIAL_CREDITS,
        paytable: Paytable | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._credits: float = initial_credits
        self._paytable = paytable if paytable is not None else Paytable()
        self._rng = rng  # passado a cada Deck novo
        self._state: GameState = GameState.IDLE
        self._bet: float = DEFAULT_BET
        self._deck: Deck | None = None
        self._hand: Hand | None = None
        self._last_outcome: RoundOutcome | None = None

        # Estado da fase de dobra
        self._pending_prize: float = 0.0
        self._double_card: Card | None = None
        self._double_outcome: DoubleOutcome | None = None
        self._poker_final_hand: Hand | None = None
        self._double_history: list[Card] = []
        self._last_double_multiplier: int = 0

    # ---- leitura ----
    @property
    def state(self) -> GameState:
        return self._state

    @property
    def credits(self) -> float:
        return self._credits

    @property
    def bet(self) -> float:
        return self._bet

    @property
    def hand(self) -> Hand | None:
        return self._hand

    @property
    def last_outcome(self) -> RoundOutcome | None:
        return self._last_outcome

    @property
    def paytable(self) -> Paytable:
        return self._paytable

    @property
    def pending_prize(self) -> float:
        return self._pending_prize

    @property
    def double_card(self) -> Card | None:
        return self._double_card

    @property
    def double_outcome(self) -> DoubleOutcome | None:
        return self._double_outcome

    @property
    def poker_final_hand(self) -> Hand | None:
        return self._poker_final_hand

    @property
    def double_history(self) -> list[Card]:
        return list(self._double_history)

    @property
    def last_double_multiplier(self) -> int:
        """Multiplicador aplicado na última jogada de dobra (0=lose, 1=tie, 2/5/10=win)."""
        return self._last_double_multiplier

    @property
    def double_cards_remaining(self) -> int:
        return self._deck.remaining if self._deck is not None else 0

    # ---- operações de aposta ----
    def set_bet(self, amount: float) -> None:
        """Ajusta a aposta antes do DEAL. Permite apenas em IDLE/BET_PLACED."""
        if self._state not in (GameState.IDLE, GameState.BET_PLACED):
            raise InvalidTransitionError(self._state, "set_bet")
        if amount < MIN_BET or amount > MAX_BET:
            raise InvalidBetError(f"aposta deve estar em [{MIN_BET}, {MAX_BET}]")
        if amount > self._credits:
            raise InsufficientCreditsError(
                f"crédito insuficiente: tem {self._credits}, pediu {amount}"
            )
        self._bet = amount
        # Define BET_PLACED como sinal de "pronto para DEAL".
        self._state = GameState.BET_PLACED

    def cancel_bet(self) -> None:
        if self._state != GameState.BET_PLACED:
            raise InvalidTransitionError(self._state, "cancel_bet")
        self._state = GameState.IDLE

    # ---- operações de rodada ----
    def deal(self) -> None:
        if self._state != GameState.BET_PLACED:
            raise InvalidTransitionError(self._state, "deal")
        if self._bet > self._credits:
            raise InsufficientCreditsError("crédito insuficiente para apostar")
        # Debita aposta no início da rodada.
        self._credits -= self._bet
        self._deck = Deck(rng=self._rng)
        cards = self._deck.draw(HAND_SIZE)
        self._hand = Hand(cards=cards)
        self._state = GameState.DEALT

    def toggle_hold(self, index: int) -> None:
        if self._state != GameState.DEALT:
            raise InvalidTransitionError(self._state, "toggle_hold")
        assert self._hand is not None
        self._hand.toggle_hold(index)

    def draw(self) -> RoundOutcome:
        """Substitui as cartas não-mantidas, avalia e prepara o pending_prize.

        O prêmio NÃO é creditado aqui. Fica em pending até take_prize() (ou
        é zerado se o jogador errar uma dobra).
        """
        if self._state != GameState.DEALT:
            raise InvalidTransitionError(self._state, "draw")
        assert self._hand is not None and self._deck is not None

        unheld = self._hand.unheld_indices()
        new_cards = self._deck.draw(len(unheld))
        self._hand = self._hand.replace_unheld(new_cards)
        self._state = GameState.DRAWN

        result = evaluate(self._hand)
        payout = self._paytable.payout(result, self._bet)
        self._pending_prize = payout
        self._poker_final_hand = self._hand
        self._state = GameState.EVALUATED

        outcome = RoundOutcome(
            final_hand=self._hand,
            result=result,
            bet=self._bet,
            payout=payout,
            credits_after=self._credits + payout,  # informativo: pré-take
        )
        self._last_outcome = outcome
        return outcome

    # ---- fase de dobra ----
    def start_double(self) -> None:
        """Entra na fase de dobra: sorteia carta virada do baralho remanescente.

        Permitido em EVALUATED (com pending > 0) ou DOUBLE_REVEALED após
        WIN/TIE. Se o baralho estiver vazio, força take_prize.
        """
        if self._state == GameState.EVALUATED:
            if self._pending_prize <= 0:
                raise InvalidTransitionError(self._state, "start_double")
        elif self._state == GameState.DOUBLE_REVEALED:
            if self._double_outcome not in (DoubleOutcome.WIN, DoubleOutcome.TIE):
                raise InvalidTransitionError(self._state, "start_double")
        else:
            raise InvalidTransitionError(self._state, "start_double")

        if self._deck is None or self._deck.remaining == 0:
            # Baralho esgotou — força levar o prêmio.
            self.take_prize()
            return

        self._double_card = self._deck.draw(1)[0]
        self._double_outcome = None
        self._state = GameState.DOUBLE_OFFERED

    def guess_big(self) -> DoubleOutcome:
        return self._resolve_guess(big=True)

    def guess_mini(self) -> DoubleOutcome:
        return self._resolve_guess(big=False)

    def _resolve_guess(self, *, big: bool) -> DoubleOutcome:
        if self._state != GameState.DOUBLE_OFFERED:
            raise InvalidTransitionError(self._state, "guess")
        assert self._double_card is not None
        v = self._double_card.rank.value_int

        if v == DOUBLE_PIVOT:
            self._double_outcome = DoubleOutcome.TIE
            self._last_double_multiplier = 1
        elif (v > DOUBLE_PIVOT and big) or (v < DOUBLE_PIVOT and not big):
            self._double_outcome = DoubleOutcome.WIN
            self._pending_prize *= DOUBLE_MULTIPLIER_BIG_MINI
            self._last_double_multiplier = DOUBLE_MULTIPLIER_BIG_MINI
        else:
            self._double_outcome = DoubleOutcome.LOSE
            self._pending_prize = 0.0
            self._last_double_multiplier = 0

        self._double_history.append(self._double_card)
        self._state = GameState.DOUBLE_REVEALED
        return self._double_outcome

    def guess_exact(self, rank: Rank, suit: Suit) -> DoubleOutcome:
        """Aposta cheia: prevê rank + naipe da próxima carta.

        Pagamentos:
        - Acertou rank E naipe: prêmio × 10
        - Acertou só rank (naipe errado): prêmio × 5
        - Errou rank: perde tudo

        Como BIG/MINI, ao ganhar o jogador pode continuar dobrando ou levar.
        Não há empate em 7 — o pivô só vale para BIG/MINI.
        """
        if self._state != GameState.DOUBLE_OFFERED:
            raise InvalidTransitionError(self._state, "guess_exact")
        assert self._double_card is not None
        revealed = self._double_card

        if revealed.rank is rank and revealed.suit is suit:
            self._double_outcome = DoubleOutcome.WIN
            self._pending_prize *= DOUBLE_MULTIPLIER_EXACT_FULL
            self._last_double_multiplier = DOUBLE_MULTIPLIER_EXACT_FULL
        elif revealed.rank is rank:
            self._double_outcome = DoubleOutcome.WIN
            self._pending_prize *= DOUBLE_MULTIPLIER_EXACT_RANK
            self._last_double_multiplier = DOUBLE_MULTIPLIER_EXACT_RANK
        else:
            self._double_outcome = DoubleOutcome.LOSE
            self._pending_prize = 0.0
            self._last_double_multiplier = 0

        self._double_history.append(revealed)
        self._state = GameState.DOUBLE_REVEALED
        return self._double_outcome

    def continue_after_reveal(self) -> None:
        """Avança após DOUBLE_REVEALED.

        - LOSE: prêmio já é 0; volta para IDLE/GAME_OVER.
        - WIN/TIE: sorteia próxima carta (start_double). Se baralho esgotou,
          o próprio start_double faz take_prize.
        """
        if self._state != GameState.DOUBLE_REVEALED:
            raise InvalidTransitionError(self._state, "continue_after_reveal")
        if self._double_outcome == DoubleOutcome.LOSE:
            self._reset_double_state()
            self._next_round_or_game_over()
        else:
            self.start_double()

    def take_prize(self) -> None:
        """Credita pending_prize ao saldo e encerra a fase de dobra."""
        if self._state not in (
            GameState.EVALUATED,
            GameState.DOUBLE_OFFERED,
            GameState.DOUBLE_REVEALED,
        ):
            raise InvalidTransitionError(self._state, "take_prize")
        self._credits += self._pending_prize
        self._pending_prize = 0.0
        self._reset_double_state()
        self._next_round_or_game_over()

    def next_round(self) -> None:
        """Alias: avança para a próxima rodada após uma rodada não-premiada."""
        self.take_prize()

    # ---- internas ----
    def _next_round_or_game_over(self) -> None:
        self._hand = None
        self._deck = None
        if self._credits < MIN_BET:
            self._state = GameState.GAME_OVER
        else:
            self._bet = min(self._bet, self._credits)
            self._state = GameState.IDLE

    def _reset_double_state(self) -> None:
        self._double_card = None
        self._double_outcome = None
        self._double_history.clear()
        self._poker_final_hand = None
        self._last_double_multiplier = 0

    # ---- controle ----
    def reset(self, initial_credits: float = INITIAL_CREDITS) -> None:
        """Reinicia a sessão (usado em GAME_OVER ou para nova partida)."""
        self._credits = initial_credits
        self._bet = DEFAULT_BET
        self._hand = None
        self._deck = None
        self._last_outcome = None
        self._pending_prize = 0.0
        self._reset_double_state()
        self._state = GameState.IDLE
