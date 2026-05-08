"""Cena principal da mesa: integra estado da sessão com renderização."""
from __future__ import annotations

import pygame

from ..config import (
    BET_STEP,
    HAND_SIZE,
    INITIAL_CREDITS,
    MAX_BET,
    MIN_BET,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from ..domain.card import Rank, Suit
from ..domain.evaluator import evaluate
from ..domain.hand_rank import HandRank
from ..game.session import (
    DoubleOutcome,
    GameSession,
    InsufficientCreditsError,
    InvalidBetError,
)
from ..game.state import GameState, InvalidTransitionError
from . import theme
from .assets import render_text
from .keybindings import KeyBindings
from .sound import SoundManager
from .widgets.button import Button
from .widgets.card_view import CardView
from .widgets.panel import LabelPanel, MessagePanel
from .widgets.paytable_view import PaytableView
from .widgets.suit_drawer import draw_suit


def _format_amount(value: float) -> str:
    """Formata número monetário: inteiro sem casas, decimal sempre com 2 casas."""
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}"


DEAL_ANIM_DURATION = 0.5
DEAL_ANIM_STAGGER = 0.08

# Tamanhos da fase de dobra
MINI_CARD_W = 54
MINI_CARD_H = 76
HISTORY_CARD_W = 34
HISTORY_CARD_H = 50
DOUBLE_CARD_W = 90
DOUBLE_CARD_H = 130

# Suspense manual: a carta vai sendo descoberta de baixo pra cima a cada
# clique no botão ABRIR. Cada clique soma REVEAL_STEP ao progresso (0..1).
REVEAL_STEP = 0.2  # 5 cliques para a carta sair completamente

# Tempo entre uma rodada de dobra e a próxima ser disparada automaticamente
# após WIN/TIE. Janela em que o jogador pode clicar LEVAR para parar.
# Quando o jogador escolheu ABRIR RAPIDO, usa o delay reduzido — ele já
# sinalizou que quer ritmo acelerado.
AUTO_CONTINUE_DELAY = 1.4
AUTO_CONTINUE_DELAY_FAST = 0.5


class TableScene:
    def __init__(
        self,
        session: GameSession,
        sound: SoundManager | None = None,
        bindings: KeyBindings | None = None,
        on_open_settings: callable | None = None,
    ) -> None:
        self.session = session
        self.sound = sound if sound is not None else SoundManager()
        self.bindings = bindings if bindings is not None else KeyBindings.load()
        self.on_open_settings = on_open_settings
        self.elapsed = 0.0
        self._deal_started_at: float | None = None
        self._anim_targets: list[int] = []

        # Modo de seleção da aposta cheia
        self._exact_mode: bool = False
        self._selected_rank: Rank | None = None
        self._selected_suit: Suit | None = None

        # Streak de acertos consecutivos na dobra (controla pitch do sino)
        self._double_streak: int = 0

        # Revelação manual: depois de BIG/MINI/CHEIO o palpite fica armazenado
        # aqui e a carta só é descoberta quando o jogador clicar em ABRIR
        # (gradual) ou ABRIR RAPIDO (de uma vez).
        self._reveal_pending_fn: callable | None = None
        self._reveal_progress: float = 0.0

        # Lock do modo "ABRIR RAPIDO": uma vez ativado pelo jogador, as
        # próximas dobras da sequência atual abrem direto, sem pedir clique
        # extra de revelação. Reseta quando ele clica ABRIR (volta ao manual)
        # ou quando a sequência de dobras termina (LEVAR/LOSE).
        self._fast_reveal_locked: bool = False

        # Auto-continuação: após WIN/TIE, dispara start_double automaticamente
        # depois deste instante. LEVAR continua disponível para interromper.
        self._auto_advance_at: float | None = None

        # Paytable lateral direita
        pt_w = 220
        pt_x = WINDOW_WIDTH - pt_w - 20
        pt_y = 100
        pt_h = 360

        play_left = 20
        play_right = pt_x - 20
        play_w = play_right - play_left

        # ---- Cartas centrais (modo POKER) ----
        total_w = HAND_SIZE * theme.CARD_W + (HAND_SIZE - 1) * theme.CARD_GAP
        start_x = play_left + (play_w - total_w) // 2
        cards_y = 200
        self.card_views: list[CardView] = []
        for i in range(HAND_SIZE):
            rect = pygame.Rect(
                start_x + i * (theme.CARD_W + theme.CARD_GAP),
                cards_y,
                theme.CARD_W,
                theme.CARD_H,
            )
            self.card_views.append(CardView(rect=rect))

        # ---- Mini cartas (modo DOBRA: mão premiada no topo) ----
        mini_total_w = HAND_SIZE * MINI_CARD_W + (HAND_SIZE - 1) * 8
        mini_start_x = play_left + (play_w - mini_total_w) // 2
        mini_y = 175
        self.mini_card_views: list[CardView] = []
        for i in range(HAND_SIZE):
            rect = pygame.Rect(
                mini_start_x + i * (MINI_CARD_W + 8),
                mini_y,
                MINI_CARD_W,
                MINI_CARD_H,
            )
            self.mini_card_views.append(CardView(rect=rect))

        # ---- Carta de dobra (esquerda, abaixo das mini cards) ----
        double_x = play_left + 50
        double_y = mini_y + MINI_CARD_H + 22
        self.double_card_view = CardView(
            rect=pygame.Rect(double_x, double_y, DOUBLE_CARD_W, DOUBLE_CARD_H)
        )

        # ---- Histórico de dobras (cartinhas à direita da carta de dobra) ----
        self._history_max = 18
        self._history_x = self.double_card_view.rect.right + 24
        self._history_y = double_y + 10

        # ---- Painéis topo ----
        panel_h = 56
        panel_top = 100
        panel_gap = 12
        panel_w = (play_w - panel_gap * 2) // 3

        self.jackpot_panel = LabelPanel(
            rect=pygame.Rect(play_left, panel_top, panel_w, panel_h),
            label="JACKPOT",
            value="0",
            label_color=theme.NEON_ORANGE,
            value_color=theme.NEON_YELLOW,
        )
        self.credit_panel = LabelPanel(
            rect=pygame.Rect(
                self.jackpot_panel.rect.right + panel_gap,
                panel_top,
                panel_w,
                panel_h,
            ),
            label="CREDITO",
            value=_format_amount(self.session.credits),
            label_color=theme.NEON_GREEN,
            value_color=theme.NEON_CYAN,
        )
        self.bet_panel = LabelPanel(
            rect=pygame.Rect(
                self.credit_panel.rect.right + panel_gap,
                panel_top,
                panel_w,
                panel_h,
            ),
            label="APOSTA",
            value=_format_amount(self.session.bet),
            label_color=theme.NEON_MAGENTA,
            value_color=theme.NEON_YELLOW,
        )

        # ---- Mensagem (entre cartas e botões) ----
        msg_top = cards_y + theme.CARD_H + 40
        self.message_panel = MessagePanel(
            rect=pygame.Rect(play_left, msg_top, play_w, 44),
            text="",
        )

        # Painéis da fase DOBRA (linha de 3 colunas, mesmo y do msg_panel)
        col_gap = 8
        col_w = (play_w - col_gap * 2) // 3
        self.prize_panel = LabelPanel(
            rect=pygame.Rect(play_left, msg_top, col_w, 44),
            label="PREMIO",
            value="0",
            label_color=theme.MSG_WIN,
            value_color=theme.MSG_WIN,
        )
        self.remaining_panel = LabelPanel(
            rect=pygame.Rect(
                play_left + col_w + col_gap, msg_top, col_w, 44
            ),
            label="CARTAS",
            value="0",
            label_color=theme.FG_GREEN,
            value_color=theme.FG_AMBER,
        )
        self.double_msg_panel = MessagePanel(
            rect=pygame.Rect(
                play_left + 2 * (col_w + col_gap), msg_top, col_w, 44
            ),
            text="",
        )

        # ---- Paytable ----
        self.paytable_view = PaytableView(
            rect=pygame.Rect(pt_x, pt_y, pt_w, pt_h),
            paytable=self.session.paytable,
            bet=int(self.session.bet),
        )

        # ---- Botões ----
        btn_y = msg_top + 60
        btn_h = 44
        btn_gap = 8
        n_btns = 6
        btn_w = (play_w - btn_gap * (n_btns - 1)) // n_btns

        def make_btn(slot: int, label: str, cb, *, big_size: bool = False) -> Button:
            return Button(
                rect=pygame.Rect(
                    play_left + slot * (btn_w + btn_gap),
                    btn_y,
                    btn_w,
                    btn_h,
                ),
                label=label,
                on_click=cb,
                size=theme.FONT_NORMAL_SIZE if big_size else theme.FONT_SMALL_SIZE,
            )

        # Botões da fase POKER
        self.bet_minus_btn = make_btn(0, "- APOSTA", self._on_bet_minus)
        self.bet_plus_btn = make_btn(1, "+ APOSTA", self._on_bet_plus)
        self.max_bet_btn = make_btn(2, "APOSTA MAX", self._on_max_bet)
        self.deal_btn = make_btn(3, "DISTRIBUIR", self._on_deal)
        self.draw_btn = make_btn(4, "TROCAR", self._on_draw)
        self.next_btn = make_btn(5, "PROXIMA", self._on_next)

        # Botões da fase DOBRA. Layouts variam:
        # - EVALUATED com prêmio: DOBRAR / LEVAR (2 botões)
        # - DOUBLE_OFFERED: BIG / MINI / CHEIO / LEVAR (4 botões)
        # - DOUBLE_REVEALED win/tie: DOBRAR / LEVAR (2 botões)
        # - DOUBLE_REVEALED lose: CONTINUAR (1 botão)
        big_w_2 = (play_w - btn_gap) // 2
        big_w_4 = (play_w - btn_gap * 3) // 4

        self.dobrar_btn = Button(
            rect=pygame.Rect(play_left, btn_y, big_w_2, btn_h),
            label="DOBRAR",
            on_click=self._on_start_double,
            size=theme.FONT_NORMAL_SIZE,
        )
        self.big_btn = Button(
            rect=pygame.Rect(play_left + 0 * (big_w_4 + btn_gap), btn_y, big_w_4, btn_h),
            label="BIG (>7)",
            on_click=self._on_guess_big,
            size=theme.FONT_NORMAL_SIZE,
        )
        self.mini_btn = Button(
            rect=pygame.Rect(play_left + 1 * (big_w_4 + btn_gap), btn_y, big_w_4, btn_h),
            label="MINI (<7)",
            on_click=self._on_guess_mini,
            size=theme.FONT_NORMAL_SIZE,
        )
        self.cheio_btn = Button(
            rect=pygame.Rect(play_left + 2 * (big_w_4 + btn_gap), btn_y, big_w_4, btn_h),
            label="CHEIO",
            on_click=self._on_open_exact,
            size=theme.FONT_NORMAL_SIZE,
        )
        self.take_btn_4 = Button(
            rect=pygame.Rect(play_left + 3 * (big_w_4 + btn_gap), btn_y, big_w_4, btn_h),
            label="LEVAR",
            on_click=self._on_take_prize,
            size=theme.FONT_NORMAL_SIZE,
        )
        self.take_btn = Button(
            rect=pygame.Rect(play_left + big_w_2 + btn_gap, btn_y, big_w_2, btn_h),
            label="LEVAR",
            on_click=self._on_take_prize,
            size=theme.FONT_NORMAL_SIZE,
        )
        self.continue_btn = Button(
            rect=pygame.Rect(play_left, btn_y, big_w_2, btn_h),
            label="CONTINUAR",
            on_click=self._on_continue_after_reveal,
            size=theme.FONT_NORMAL_SIZE,
        )
        # Botões da revelação manual: aparecem após BIG/MINI/CHEIO.
        # ABRIR RAPIDO descobre tudo de uma vez; ABRIR sobe a carta de
        # baixo pra cima em REVEAL_STEP por clique.
        self.reveal_fast_btn = Button(
            rect=pygame.Rect(play_left, btn_y, big_w_2, btn_h),
            label="ABRIR RAPIDO",
            on_click=self._on_reveal_fast,
            size=theme.FONT_NORMAL_SIZE,
        )
        self.reveal_slow_btn = Button(
            rect=pygame.Rect(play_left + big_w_2 + btn_gap, btn_y, big_w_2, btn_h),
            label="ABRIR",
            on_click=self._on_reveal_step,
            size=theme.FONT_NORMAL_SIZE,
        )

        # Botões do overlay de aposta cheia (rank + naipe)
        self._build_exact_overlay(
            play_left=play_left, play_w=play_w, btn_y=btn_y, btn_h=btn_h, btn_gap=btn_gap
        )

        # Botão OPÇÕES (canto superior do título)
        self.settings_btn = Button(
            rect=pygame.Rect(WINDOW_WIDTH - 110, 28, 90, 28),
            label="OPCOES",
            on_click=self._on_open_settings_click,
            size=theme.FONT_SMALL_SIZE,
        )

        # Botões HOLD (logo abaixo das cartas grandes — fase POKER)
        self.hold_buttons: list[Button] = []
        for i, cv in enumerate(self.card_views):
            rect = pygame.Rect(cv.rect.left, cv.rect.bottom + 6, theme.CARD_W, 24)
            self.hold_buttons.append(
                Button(
                    rect=rect,
                    label="HOLD",
                    on_click=lambda i=i: self._on_toggle_hold(i),
                    size=theme.FONT_SMALL_SIZE,
                )
            )

        self._sync_view()

    def _build_exact_overlay(
        self,
        *,
        play_left: int,
        play_w: int,
        btn_y: int,
        btn_h: int,
        btn_gap: int,
    ) -> None:
        """Cria botões para seleção de rank + naipe na aposta cheia."""
        # Linha de ranks (13 botões pequenos)
        rank_y = 220
        rank_gap = 4
        rank_n = 13
        rank_w = (play_w - rank_gap * (rank_n - 1)) // rank_n
        rank_h = 36
        ranks = list(Rank)  # 2..A

        self.rank_buttons: list[Button] = []
        for i, r in enumerate(ranks):
            self.rank_buttons.append(
                Button(
                    rect=pygame.Rect(
                        play_left + i * (rank_w + rank_gap),
                        rank_y,
                        rank_w,
                        rank_h,
                    ),
                    label=r.label,
                    on_click=lambda r=r: self._on_select_rank(r),
                    size=theme.FONT_SMALL_SIZE,
                )
            )

        # Linha de naipes (4 botões maiores)
        suit_y = rank_y + rank_h + 12
        suit_n = 4
        suit_gap = 8
        suit_w = (play_w - suit_gap * (suit_n - 1)) // suit_n
        suit_h = 50
        suits = [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]
        self.suit_buttons: list[Button] = []
        for i, s in enumerate(suits):
            self.suit_buttons.append(
                Button(
                    rect=pygame.Rect(
                        play_left + i * (suit_w + suit_gap),
                        suit_y,
                        suit_w,
                        suit_h,
                    ),
                    label=s.symbol,
                    on_click=lambda s=s: self._on_select_suit(s),
                    size=theme.FONT_BIG_SIZE,
                )
            )

        # Botões de ação (CONFIRMAR / VOLTAR) na linha dos botões originais
        confirm_w = (play_w - btn_gap) // 2
        self.confirm_exact_btn = Button(
            rect=pygame.Rect(play_left, btn_y, confirm_w, btn_h),
            label="CONFIRMAR",
            on_click=self._on_confirm_exact,
            size=theme.FONT_NORMAL_SIZE,
        )
        self.cancel_exact_btn = Button(
            rect=pygame.Rect(
                play_left + confirm_w + btn_gap, btn_y, confirm_w, btn_h
            ),
            label="VOLTAR",
            on_click=self._on_cancel_exact,
            size=theme.FONT_NORMAL_SIZE,
        )

    # ---- handlers da aposta cheia ----
    def _on_open_exact(self) -> None:
        if self.session.state != GameState.DOUBLE_OFFERED:
            return
        self._exact_mode = True
        self._selected_rank = None
        self._selected_suit = None
        self.double_msg_panel.text = "CHEIO"
        self.double_msg_panel.color = theme.MSG_INFO

    def _on_select_rank(self, rank: Rank) -> None:
        self._selected_rank = rank

    def _on_select_suit(self, suit: Suit) -> None:
        self._selected_suit = suit

    def _on_confirm_exact(self) -> None:
        if self._selected_rank is None or self._selected_suit is None:
            return
        rank = self._selected_rank
        suit = self._selected_suit
        self._exact_mode = False
        self._selected_rank = None
        self._selected_suit = None
        self._begin_guess(lambda: self.session.guess_exact(rank, suit))

    def _on_cancel_exact(self) -> None:
        self._exact_mode = False
        self._selected_rank = None
        self._selected_suit = None
        self.double_msg_panel.text = "BIG OU MINI?"
        self.double_msg_panel.color = theme.MSG_INFO

    def _on_open_settings_click(self) -> None:
        if self.on_open_settings is not None:
            self.on_open_settings()

    # ---- handlers de input (POKER) ----
    def _on_bet_minus(self) -> None:
        try:
            new_bet = round(max(MIN_BET, self.session.bet - BET_STEP), 2)
            self.session.set_bet(new_bet)
        except (InvalidBetError, InsufficientCreditsError, InvalidTransitionError):
            pass
        self._sync_view()

    def _on_bet_plus(self) -> None:
        try:
            new_bet = round(min(MAX_BET, self.session.bet + BET_STEP), 2)
            self.session.set_bet(new_bet)
        except (InvalidBetError, InsufficientCreditsError, InvalidTransitionError):
            pass
        self._sync_view()

    def _on_max_bet(self) -> None:
        try:
            new_bet = round(min(MAX_BET, self.session.credits), 2)
            new_bet = max(MIN_BET, new_bet)
            self.session.set_bet(new_bet)
        except (InvalidBetError, InsufficientCreditsError, InvalidTransitionError):
            pass
        self._sync_view()

    def _on_deal(self) -> None:
        if self.session.state == GameState.IDLE:
            try:
                self.session.set_bet(self.session.bet)
            except (InvalidBetError, InsufficientCreditsError):
                return
        try:
            self.session.deal()
            self._start_deal_animation(list(range(HAND_SIZE)))
            # Avalia a mão inicial: se já tem combinação, avisa o jogador
            if self.session.hand is not None:
                preview = evaluate(self.session.hand)
                if preview.rank != HandRank.HIGH_CARD:
                    self.message_panel.text = f"JA TEM {preview.rank.label}!"
                    self.message_panel.color = theme.MSG_WIN
                else:
                    self.message_panel.text = "BOA SORTE"
                    self.message_panel.color = theme.MSG_INFO
        except (InvalidTransitionError, InsufficientCreditsError):
            pass
        self._sync_view()

    def _on_draw(self) -> None:
        replaced: list[int] = []
        if self.session.hand is not None:
            replaced = self.session.hand.unheld_indices()
        try:
            outcome = self.session.draw()
            if replaced:
                self._start_deal_animation(replaced)
            if outcome.won:
                self.message_panel.text = (
                    f"{outcome.result.label}  +{_format_amount(outcome.payout)}"
                )
                self.message_panel.color = theme.MSG_WIN
                self.sound.play("win")
            else:
                self.message_panel.text = "TENTE NOVAMENTE"
                self.message_panel.color = theme.MSG_LOSE
                self.sound.play("lose")
            self._double_streak = 0
        except InvalidTransitionError:
            pass
        self._sync_view()

    def _on_next(self) -> None:
        try:
            self.session.next_round()
            if self.session.state == GameState.GAME_OVER:
                self.message_panel.text = "FIM DE JOGO"
                self.message_panel.color = theme.MSG_LOSE
            else:
                self.message_panel.text = ""
        except InvalidTransitionError:
            pass
        self._sync_view()

    def _on_toggle_hold(self, index: int) -> None:
        try:
            self.session.toggle_hold(index)
        except InvalidTransitionError:
            pass
        self._sync_view()

    # ---- handlers de input (DOBRA) ----
    def _on_start_double(self) -> None:
        try:
            self.session.start_double()
            if self.session.state == GameState.DOUBLE_OFFERED:
                self.double_msg_panel.text = "BIG OU MINI?"
                self.double_msg_panel.color = theme.MSG_INFO
                self.sound.play("double_offered")
        except InvalidTransitionError:
            pass
        self._sync_view()

    def _on_guess_big(self) -> None:
        self._begin_guess(self.session.guess_big)

    def _on_guess_mini(self) -> None:
        self._begin_guess(self.session.guess_mini)

    # ---- núcleo do palpite (sempre adia até o jogador clicar ABRIR) ----
    def _begin_guess(self, guess_fn: callable) -> None:
        """Registra o palpite.

        Se o jogador já travou modo ABRIR RAPIDO nesta sequência, aplica
        direto. Caso contrário, a carta só é descoberta quando ele clicar
        em ABRIR (gradual) ou ABRIR RAPIDO (de uma vez).
        """
        if self.session.state != GameState.DOUBLE_OFFERED:
            return
        if self._reveal_pending_fn is not None:
            return  # já tem um palpite em curso
        self._auto_advance_at = None

        # Modo rápido travado: pula a etapa dos botões ABRIR/ABRIR RAPIDO.
        if self._fast_reveal_locked:
            self._apply_guess(guess_fn)
            return

        self._reveal_pending_fn = guess_fn
        self._reveal_progress = 0.0
        self.double_msg_panel.text = "ABRA A CARTA"
        self.double_msg_panel.color = theme.NEON_YELLOW
        self._sync_view()

    def _on_reveal_fast(self) -> None:
        """Descobre a carta inteira em um clique e trava o modo rápido
        para as próximas dobras da sequência.
        """
        if self._reveal_pending_fn is None:
            return
        self._fast_reveal_locked = True
        fn = self._reveal_pending_fn
        self._reveal_pending_fn = None
        self._reveal_progress = 1.0
        self._apply_guess(fn)

    def _on_reveal_step(self) -> None:
        """Sobe a carta um passo (REVEAL_STEP) — clique repetido revela tudo.
        Cancela o lock de modo rápido (jogador voltou ao ritmo manual).
        """
        if self._reveal_pending_fn is None:
            return
        self._fast_reveal_locked = False
        self._reveal_progress = min(1.0, self._reveal_progress + REVEAL_STEP)
        self.sound.play("double_offered")
        if self._reveal_progress >= 1.0:
            fn = self._reveal_pending_fn
            self._reveal_pending_fn = None
            self._apply_guess(fn)
        else:
            self._sync_view()

    def _apply_guess(self, guess_fn: callable) -> None:
        try:
            guess_fn()
            self._update_double_message()
            self._play_double_outcome_sound()
        except InvalidTransitionError:
            pass
        # Após resolver, se WIN/TIE programa auto-advance. Delay reduzido
        # quando o jogador travou modo rápido.
        outcome = self.session.double_outcome
        if (
            self.session.state == GameState.DOUBLE_REVEALED
            and outcome in (DoubleOutcome.WIN, DoubleOutcome.TIE)
        ):
            delay = AUTO_CONTINUE_DELAY_FAST if self._fast_reveal_locked else AUTO_CONTINUE_DELAY
            self._auto_advance_at = self.elapsed + delay
        else:
            self._auto_advance_at = None
        self._sync_view()

    def _reveal_active(self) -> bool:
        return self._reveal_pending_fn is not None

    def _cancel_reveal(self) -> None:
        self._reveal_pending_fn = None
        self._reveal_progress = 0.0

    def _play_double_outcome_sound(self) -> None:
        outcome = self.session.double_outcome
        if outcome is DoubleOutcome.WIN:
            self._double_streak += 1
            self.sound.play_bell(level=self._double_streak - 1)
        elif outcome is DoubleOutcome.TIE:
            self.sound.play("tie")
        elif outcome is DoubleOutcome.LOSE:
            self.sound.play("lose")
            self._double_streak = 0

    def _on_continue_after_reveal(self) -> None:
        self._auto_advance_at = None
        self._cancel_reveal()
        try:
            self.session.continue_after_reveal()
            if self.session.state == GameState.DOUBLE_OFFERED:
                self.double_msg_panel.text = "BIG OU MINI?"
                self.double_msg_panel.color = theme.MSG_INFO
                self.sound.play("double_offered")
            elif self.session.state == GameState.IDLE:
                # LOSE encerrou a sequência: limpa o lock de modo rápido.
                self._fast_reveal_locked = False
                self.message_panel.text = "PERDEU TUDO"
                self.message_panel.color = theme.MSG_LOSE
                self.double_msg_panel.text = ""
                self._double_streak = 0
        except InvalidTransitionError:
            pass
        self._sync_view()

    def _on_take_prize(self) -> None:
        # LEVAR cancela qualquer revelação em curso, auto-advance pendente
        # e o lock de modo rápido (próxima sequência começa do zero).
        self._cancel_reveal()
        self._auto_advance_at = None
        self._fast_reveal_locked = False
        try:
            credited = self.session.pending_prize
            self.session.take_prize()
            if credited > 0:
                self.message_panel.text = f"LEVOU {_format_amount(credited)}"
                self.message_panel.color = theme.MSG_WIN
                self.sound.play("take")
            else:
                self.message_panel.text = ""
            self._double_streak = 0
        except InvalidTransitionError:
            pass
        self._sync_view()

    def _update_double_message(self) -> None:
        outcome = self.session.double_outcome
        mult = self.session.last_double_multiplier
        if outcome is DoubleOutcome.WIN:
            if mult == 10:
                self.double_msg_panel.text = "CHEIO! 10x"
            elif mult == 5:
                self.double_msg_panel.text = "RANK! 5x"
            else:
                self.double_msg_panel.text = "ACERTOU!"
            self.double_msg_panel.color = theme.MSG_WIN
        elif outcome is DoubleOutcome.TIE:
            self.double_msg_panel.text = "EMPATE"
            self.double_msg_panel.color = theme.MSG_INFO
        elif outcome is DoubleOutcome.LOSE:
            self.double_msg_panel.text = "PERDEU"
            self.double_msg_panel.color = theme.MSG_LOSE

    # ---- ciclo de vida ----
    def _sync_view(self) -> None:
        st = self.session.state

        # Cartas grandes (fase POKER)
        hand = self.session.hand
        for i, cv in enumerate(self.card_views):
            if hand is None:
                cv.card = None
                cv.held = False
                cv.revealed = False
            else:
                cv.card = hand[i]
                cv.held = i in hand.holds
                cv.revealed = True

        # Mini cartas (mão premiada exibida durante DOBRA)
        poker_hand = self.session.poker_final_hand
        for i, cv in enumerate(self.mini_card_views):
            if poker_hand is None:
                cv.card = None
                cv.revealed = False
            else:
                cv.card = poker_hand[i]
                cv.revealed = True

        # Carta de dobra: virada em OFFERED, revelada em REVEALED.
        # Quando a revelação manual está em curso, _render_double_phase
        # desenha a carta sendo descoberta de baixo pra cima — o draw
        # padrão do CardView não é usado.
        if st == GameState.DOUBLE_OFFERED:
            self.double_card_view.card = self.session.double_card
            self.double_card_view.revealed = False
        elif st == GameState.DOUBLE_REVEALED:
            self.double_card_view.card = self.session.double_card
            self.double_card_view.revealed = True
        else:
            self.double_card_view.card = None
            self.double_card_view.revealed = False

        # Painéis
        self.credit_panel.value = _format_amount(self.session.credits)
        self.bet_panel.value = _format_amount(self.session.bet)
        self.paytable_view.bet = self.session.bet

        max_mult = max((e.multiplier for e in self.session.paytable), default=0.0)
        self.jackpot_panel.value = _format_amount(max_mult * self.session.bet)

        self.prize_panel.value = _format_amount(self.session.pending_prize)
        self.remaining_panel.value = str(self.session.double_cards_remaining)

        outcome = self.session.last_outcome
        if (
            st in (GameState.EVALUATED, GameState.DOUBLE_OFFERED, GameState.DOUBLE_REVEALED)
            and outcome is not None
            and outcome.result.rank != HandRank.HIGH_CARD
        ):
            self.paytable_view.highlight = outcome.result.rank
        else:
            self.paytable_view.highlight = None

        # Preview: mão inicial em DEALT já tem combinação? Mostra piscando.
        preview = None
        if st == GameState.DEALT and self.session.hand is not None:
            preview_result = evaluate(self.session.hand)
            if preview_result.rank != HandRank.HIGH_CARD:
                preview = preview_result.rank
        self.paytable_view.preview_highlight = preview
        self.paytable_view.elapsed = self.elapsed

        # Botões POKER
        in_bet_phase = st in (GameState.IDLE, GameState.BET_PLACED)
        self.bet_minus_btn.enabled = in_bet_phase
        self.bet_plus_btn.enabled = in_bet_phase
        self.max_bet_btn.enabled = in_bet_phase
        self.deal_btn.enabled = in_bet_phase and self.session.credits >= self.session.bet
        self.draw_btn.enabled = st == GameState.DEALT
        # NEXT só faz sentido em EVALUATED sem prêmio (rodada perdida) ou GAME_OVER
        self.next_btn.enabled = (
            st == GameState.EVALUATED and self.session.pending_prize <= 0
        )

        for btn in self.hold_buttons:
            btn.enabled = st == GameState.DEALT

        # Botões DOBRA
        evaluated_with_prize = (
            st == GameState.EVALUATED and self.session.pending_prize > 0
        )
        revealed_can_continue = (
            st == GameState.DOUBLE_REVEALED
            and self.session.double_outcome in (DoubleOutcome.WIN, DoubleOutcome.TIE)
        )
        revealed_lost = (
            st == GameState.DOUBLE_REVEALED
            and self.session.double_outcome == DoubleOutcome.LOSE
        )
        revealing = self._reveal_active()
        self.dobrar_btn.enabled = (evaluated_with_prize or revealed_can_continue) and not revealing
        self.big_btn.enabled = st == GameState.DOUBLE_OFFERED and not revealing
        self.mini_btn.enabled = st == GameState.DOUBLE_OFFERED and not revealing
        self.cheio_btn.enabled = st == GameState.DOUBLE_OFFERED and not revealing
        self.take_btn_4.enabled = st == GameState.DOUBLE_OFFERED and not revealing
        # LEVAR continua ativo durante a janela de auto-advance para o
        # jogador interromper a sequência de dobras.
        self.take_btn.enabled = (
            evaluated_with_prize or st == GameState.DOUBLE_OFFERED or revealed_can_continue
        ) and not revealing
        self.continue_btn.enabled = revealed_lost and not revealing
        # Botões da revelação manual
        self.reveal_fast_btn.enabled = revealing
        self.reveal_slow_btn.enabled = revealing

    def handle_event(self, event: pygame.event.Event) -> None:
        st = self.session.state
        in_double_phase = st in (GameState.DOUBLE_OFFERED, GameState.DOUBLE_REVEALED)

        # Botão OPÇÕES sempre recebe eventos
        self.settings_btn.handle_event(event)

        # Cliques nas cartas alternam HOLD durante DEALT
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not in_double_phase:
            for i, cv in enumerate(self.card_views):
                if cv.contains(event.pos) and st == GameState.DEALT:
                    self._on_toggle_hold(i)
                    return

        # Em exact_mode, os botões de rank e naipe também recebem eventos
        # (mas seu desenho fica a cargo de _render_exact_overlay).
        if self._exact_mode and st == GameState.DOUBLE_OFFERED:
            for btn in self.rank_buttons:
                btn.handle_event(event)
            for btn in self.suit_buttons:
                btn.handle_event(event)

        active_buttons = self._active_buttons()
        for btn in active_buttons:
            btn.handle_event(event)

        if event.type == pygame.KEYDOWN:
            self._handle_key(event.key)

    def _handle_key(self, key: int) -> None:
        st = self.session.state
        b = self.bindings

        # ENTER e SPACE compartilham a ação "advance"
        if key == b.get("advance") or key == pygame.K_SPACE:
            if st in (GameState.IDLE, GameState.BET_PLACED):
                self._on_deal()
            elif st == GameState.DEALT:
                self._on_draw()
            elif st == GameState.EVALUATED:
                if self.session.pending_prize > 0:
                    self._on_take_prize()
                else:
                    self._on_next()
            elif st == GameState.DOUBLE_REVEALED:
                if self.session.double_outcome == DoubleOutcome.LOSE:
                    self._on_continue_after_reveal()
                else:
                    self._on_take_prize()
            return

        # HOLD 1..5
        for i in range(5):
            if key == b.get(f"hold_{i + 1}"):
                if st == GameState.DEALT:
                    self._on_toggle_hold(i)
                return

        # Teclas da revelação manual têm prioridade quando há palpite pendente.
        if self._reveal_active():
            if key == b.get("reveal_step"):
                self._on_reveal_step()
                return
            if key == b.get("reveal_fast"):
                self._on_reveal_fast()
                return

        if key == b.get("bet_plus"):
            self._on_bet_plus()
        elif key == b.get("bet_minus"):
            self._on_bet_minus()
        elif key == b.get("double_start") and (
            (st == GameState.EVALUATED and self.session.pending_prize > 0)
            or (
                st == GameState.DOUBLE_REVEALED
                and self.session.double_outcome in (DoubleOutcome.WIN, DoubleOutcome.TIE)
            )
        ):
            if st == GameState.DOUBLE_REVEALED:
                self._on_continue_after_reveal()
            else:
                self._on_start_double()
        elif (
            key == b.get("double_big")
            and st == GameState.DOUBLE_OFFERED
            and not self._exact_mode
            and not self._reveal_active()
        ):
            self._on_guess_big()
        elif (
            key == b.get("double_mini")
            and st == GameState.DOUBLE_OFFERED
            and not self._exact_mode
            and not self._reveal_active()
        ):
            self._on_guess_mini()
        elif (
            key == b.get("double_exact")
            and st == GameState.DOUBLE_OFFERED
            and not self._exact_mode
            and not self._reveal_active()
        ):
            self._on_open_exact()
        elif key == b.get("exact_back") and self._exact_mode:
            self._on_cancel_exact()
        elif key == b.get("take_prize") and self.session.pending_prize > 0:
            self._on_take_prize()
        elif key == b.get("restart") and st == GameState.GAME_OVER:
            self.session.reset(initial_credits=INITIAL_CREDITS)
            self.message_panel.text = ""
            self._sync_view()
        elif key == b.get("open_settings") and self.on_open_settings is not None:
            self.on_open_settings()

    def _active_buttons(self) -> list[Button]:
        st = self.session.state
        # Revelação manual em curso: só os botões de ABRIR funcionam.
        if self._reveal_active():
            return [self.reveal_fast_btn, self.reveal_slow_btn]
        # Overlay da aposta cheia tem prioridade.
        # Os rank_buttons/suit_buttons recebem eventos pelo handle_event,
        # mas o desenho passa por _render_exact_overlay (que destaca
        # selecionados). Aqui só retornamos os de ação (CONFIRMAR/VOLTAR).
        if self._exact_mode and st == GameState.DOUBLE_OFFERED:
            return [self.confirm_exact_btn, self.cancel_exact_btn]
        if st in (GameState.DOUBLE_OFFERED, GameState.DOUBLE_REVEALED) or (
            st == GameState.EVALUATED and self.session.pending_prize > 0
        ):
            outcome = self.session.double_outcome
            if st == GameState.DOUBLE_REVEALED and outcome == DoubleOutcome.LOSE:
                return [self.continue_btn]
            if st == GameState.DOUBLE_REVEALED and outcome in (DoubleOutcome.WIN, DoubleOutcome.TIE):
                return [self.dobrar_btn, self.take_btn]
            if st == GameState.DOUBLE_OFFERED:
                return [self.big_btn, self.mini_btn, self.cheio_btn, self.take_btn_4]
            # EVALUATED com prêmio
            return [self.dobrar_btn, self.take_btn]
        # Fase POKER: botões originais
        buttons = [
            self.bet_minus_btn,
            self.bet_plus_btn,
            self.max_bet_btn,
            self.deal_btn,
            self.draw_btn,
            self.next_btn,
        ]
        if st == GameState.DEALT:
            buttons.extend(self.hold_buttons)
        return buttons

    def update(self, dt: float) -> None:
        self.elapsed += dt
        if self._deal_started_at is not None:
            t = self.elapsed - self._deal_started_at
            for order, idx in enumerate(self._anim_targets):
                start = order * DEAL_ANIM_STAGGER
                local = max(0.0, min(1.0, (t - start) / DEAL_ANIM_DURATION))
                self.card_views[idx].deal_progress = local
            total_done = (len(self._anim_targets) - 1) * DEAL_ANIM_STAGGER + DEAL_ANIM_DURATION
            if t >= total_done:
                for idx in self._anim_targets:
                    self.card_views[idx].deal_progress = 1.0
                self._deal_started_at = None
                self._anim_targets = []

        # Auto-continuação: dispara start_double quando atinge o tempo.
        if (
            self._auto_advance_at is not None
            and self.elapsed >= self._auto_advance_at
            and self.session.state == GameState.DOUBLE_REVEALED
            and self.session.double_outcome in (DoubleOutcome.WIN, DoubleOutcome.TIE)
        ):
            self._on_continue_after_reveal()

    def _start_deal_animation(self, indices: list[int]) -> None:
        self._anim_targets = list(indices)
        self._deal_started_at = self.elapsed
        for idx in indices:
            self.card_views[idx].deal_progress = 0.0

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DARK)
        self._draw_title(surface)
        self.settings_btn.draw(surface)
        self.credit_panel.draw(surface)
        self.bet_panel.draw(surface)
        self.jackpot_panel.draw(surface)
        # Pulso da preview-highlight depende do tempo: atualiza a cada frame
        self.paytable_view.elapsed = self.elapsed
        self.paytable_view.draw(surface)

        st = self.session.state
        in_double = st in (GameState.DOUBLE_OFFERED, GameState.DOUBLE_REVEALED) or (
            st == GameState.EVALUATED and self.session.pending_prize > 0
        )

        if in_double:
            self._render_double_phase(surface)
        else:
            self._render_poker_phase(surface)

        # Painel de mensagem (POKER) ou linha PRÊMIO+RESTANTES+MENSAGEM (DOBRA)
        if in_double:
            self.prize_panel.draw(surface)
            self.remaining_panel.draw(surface)
            self.double_msg_panel.draw(surface)
        else:
            self.message_panel.draw(surface)

        # Botões ativos do estado
        for btn in self._active_buttons():
            btn.draw(surface)

        self._draw_help(surface)

    def _render_poker_phase(self, surface: pygame.Surface) -> None:
        for cv in self.card_views:
            cv.draw(surface, self.elapsed)
        if self.session.state == GameState.DEALT:
            for btn in self.hold_buttons:
                btn.draw(surface)

    def _render_double_phase(self, surface: pygame.Surface) -> None:
        if self._exact_mode and self.session.state == GameState.DOUBLE_OFFERED:
            self._render_exact_overlay(surface)
            return

        # Mão premiada em miniatura
        label = render_text("MAO PREMIADA", theme.FONT_SMALL_SIZE, theme.FG_AMBER)
        surface.blit(
            label,
            (self.mini_card_views[0].rect.left, self.mini_card_views[0].rect.top - 14),
        )
        for cv in self.mini_card_views:
            self._draw_mini_card(surface, cv)

        # Etiqueta DOBRA acima da carta
        dbl_label = render_text("DOBRA", theme.FONT_SMALL_SIZE, theme.NEON_MAGENTA, bold=True)
        surface.blit(
            dbl_label,
            (
                self.double_card_view.rect.centerx - dbl_label.get_width() // 2,
                self.double_card_view.rect.top - 14,
            ),
        )

        # Carta de dobra grande (esquerda) — se a revelação manual estiver
        # em curso, desenha face parcialmente descoberta (cortina subindo).
        if self._reveal_active():
            self._draw_partial_reveal_card(surface, self._reveal_progress)
        else:
            self.double_card_view.draw(surface, self.elapsed)

        # Histórico das tentativas anteriores (direita da carta de dobra).
        history = self.session.double_history
        if history:
            self._render_history(surface, history)

    def _draw_partial_reveal_card(self, surface: pygame.Surface, progress: float) -> None:
        """Desenha a carta de dobra sendo descoberta de baixo pra cima.

        progress=0 → carta totalmente coberta (mostra o verso)
        progress=1 → carta totalmente revelada (face visível)

        Implementação: desenha a face inteira, depois sobrepõe a parte
        superior (1-progress) com o padrão do verso, dando a impressão
        de uma cortina subindo.
        """
        rect = self.double_card_view.rect
        card = self.session.double_card
        if card is None:
            self.double_card_view.draw(surface, self.elapsed)
            return

        # 1) Face completa
        pygame.draw.rect(surface, theme.CARD_FACE, rect, border_radius=theme.CARD_RADIUS)
        pygame.draw.rect(
            surface, theme.CARD_BORDER, rect, width=3, border_radius=theme.CARD_RADIUS
        )
        suit_color = theme.SUIT_RED if card.suit.color == "vermelho" else theme.SUIT_BLACK
        rank_size = max(14, rect.height // 6)
        small_suit_size = max(10, rect.height // 9)
        big_suit_size = max(28, rect.height // 2)
        rank_surf = render_text(card.rank.label, rank_size, suit_color, bold=True)

        margin = 6
        surface.blit(rank_surf, (rect.left + margin, rect.top + margin))
        suit_rect_tl = pygame.Rect(
            rect.left + margin,
            rect.top + margin + rank_surf.get_height() + 2,
            small_suit_size,
            small_suit_size,
        )
        draw_suit(surface, card.suit, suit_rect_tl, suit_color)

        big_rect = pygame.Rect(0, 0, big_suit_size, big_suit_size)
        big_rect.center = rect.center
        draw_suit(surface, card.suit, big_rect, suit_color)

        rank_br = pygame.transform.rotate(rank_surf, 180)
        surface.blit(
            rank_br,
            (
                rect.right - margin - rank_br.get_width(),
                rect.bottom - margin - rank_br.get_height(),
            ),
        )
        suit_rect_br = pygame.Rect(
            rect.right - margin - small_suit_size,
            rect.bottom - margin - rank_br.get_height() - 2 - small_suit_size,
            small_suit_size,
            small_suit_size,
        )
        draw_suit(surface, card.suit, suit_rect_br, suit_color)

        # 2) Cortina superior cobrindo (1-progress) da altura
        cover_h = int(rect.height * (1.0 - progress))
        if cover_h > 0:
            cover_rect = pygame.Rect(rect.left, rect.top, rect.width, cover_h)
            original_clip = surface.get_clip()
            surface.set_clip(cover_rect)
            # Desenha o verso completo, mas o clip mantém só a parte de cima
            pygame.draw.rect(
                surface, theme.CARD_BACK, rect, border_radius=theme.CARD_RADIUS
            )
            for i in range(-rect.height, rect.width, 8):
                pygame.draw.line(
                    surface,
                    theme.NEON_MAGENTA,
                    (rect.left + max(i, 0), rect.top + max(-i, 0)),
                    (
                        rect.left + min(i + rect.height, rect.width),
                        rect.top + min(rect.height, rect.width - i),
                    ),
                    1,
                )
            pygame.draw.rect(
                surface, theme.CARD_BORDER, rect, width=3, border_radius=theme.CARD_RADIUS
            )
            surface.set_clip(original_clip)
            # Linha brilhante na borda inferior da cortina (efeito de "peeling")
            edge_y = rect.top + cover_h
            pygame.draw.line(
                surface,
                theme.NEON_YELLOW,
                (rect.left + 4, edge_y),
                (rect.right - 4, edge_y),
                2,
            )

    def _render_exact_overlay(self, surface: pygame.Surface) -> None:
        # Cabeçalho explicativo
        title = render_text(
            "APOSTA CHEIA  -  RANK 5x  /  RANK+NAIPE 10x",
            theme.FONT_SMALL_SIZE,
            theme.FG_AMBER,
            bold=True,
        )
        surface.blit(
            title,
            (
                self.rank_buttons[0].rect.left,
                self.rank_buttons[0].rect.top - 28,
            ),
        )

        # Botões de rank com destaque do selecionado
        for btn in self.rank_buttons:
            self._draw_selectable_button(
                surface,
                btn,
                selected=(self._selected_rank is not None and btn.label == self._selected_rank.label),
            )

        # Botões de naipe com cores correspondentes
        for btn, suit in zip(self.suit_buttons, [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]):
            color = theme.SUIT_RED if suit.color == "vermelho" else theme.FG_WHITE
            self._draw_selectable_button(
                surface,
                btn,
                selected=(self._selected_suit is suit),
                fg_override=color,
            )

        # Resumo da seleção
        rank_str = self._selected_rank.label if self._selected_rank else "?"
        suit_str = self._selected_suit.symbol if self._selected_suit else "?"
        sel = render_text(
            f"SELECIONADO: {rank_str} {suit_str}",
            theme.FONT_NORMAL_SIZE,
            theme.MSG_WIN if (self._selected_rank and self._selected_suit) else theme.FG_DIM,
            bold=True,
        )
        sel_x = self.suit_buttons[0].rect.left
        sel_y = self.suit_buttons[0].rect.bottom + 12
        surface.blit(sel, (sel_x, sel_y))

    def _draw_selectable_button(
        self,
        surface: pygame.Surface,
        btn: Button,
        *,
        selected: bool,
        fg_override: tuple[int, int, int] | None = None,
    ) -> None:
        """Desenha um botão com destaque quando selecionado."""
        if selected:
            pygame.draw.rect(surface, theme.MSG_WIN, btn.rect, border_radius=4)
            pygame.draw.rect(surface, theme.NEON_MAGENTA, btn.rect, width=3, border_radius=4)
            label = render_text(btn.label, btn.size, theme.SUIT_BLACK, bold=True)
            surface.blit(label, label.get_rect(center=btn.rect.center))
        else:
            # Reaproveita o draw padrão, mas opcionalmente troca a cor de texto.
            btn.draw(surface)
            if fg_override is not None:
                label = render_text(btn.label, btn.size, fg_override, bold=True)
                surface.blit(label, label.get_rect(center=btn.rect.center))

    def _render_history(self, surface: pygame.Surface, history) -> None:
        items = history[-self._history_max:]
        gap = 4
        # Limita largura disponível à direita até o paytable.
        available_w = self.paytable_view.rect.left - 20 - self._history_x
        per_row = max(1, (available_w + gap) // (HISTORY_CARD_W + gap))

        label = render_text("HISTORICO", theme.FONT_SMALL_SIZE, theme.FG_DIM)
        surface.blit(label, (self._history_x, self._history_y - 14))

        for i, card in enumerate(items):
            row = i // per_row
            col = i % per_row
            rect = pygame.Rect(
                self._history_x + col * (HISTORY_CARD_W + gap),
                self._history_y + row * (HISTORY_CARD_H + gap),
                HISTORY_CARD_W,
                HISTORY_CARD_H,
            )
            tmp = CardView(rect=rect, card=card, revealed=True)
            self._draw_mini_card(surface, tmp)

    def _draw_mini_card(self, surface: pygame.Surface, cv: CardView) -> None:
        if cv.card is None or not cv.revealed:
            pygame.draw.rect(surface, theme.CARD_BACK, cv.rect, border_radius=4)
            pygame.draw.rect(surface, theme.CARD_BORDER, cv.rect, width=2, border_radius=4)
            return

        pygame.draw.rect(surface, theme.CARD_FACE, cv.rect, border_radius=4)
        pygame.draw.rect(surface, theme.CARD_BORDER, cv.rect, width=2, border_radius=4)

        suit_color = (
            theme.SUIT_RED if cv.card.suit.color == "vermelho" else theme.SUIT_BLACK
        )
        rank_size = max(10, cv.rect.height // 4)
        suit_size = max(14, cv.rect.height // 2 - 2)

        rank_surf = render_text(cv.card.rank.label, rank_size, suit_color, bold=True)
        surface.blit(rank_surf, (cv.rect.left + 3, cv.rect.top + 2))

        # Naipe vetorial centralizado, deslocado um pouco para baixo
        # para não colidir com o rank.
        suit_rect = pygame.Rect(0, 0, suit_size, suit_size)
        suit_rect.center = (cv.rect.centerx, cv.rect.centery + cv.rect.height // 8)
        draw_suit(surface, cv.card.suit, suit_rect, suit_color)

    def _draw_title(self, surface: pygame.Surface) -> None:
        title = render_text(
            "* VIDEO POKER CLASSICO *",
            theme.FONT_TITLE_SIZE,
            theme.NEON_MAGENTA,
            bold=True,
        )
        surface.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 24))
        line_y = 24 + title.get_height() + 8
        pygame.draw.line(
            surface,
            theme.NEON_CYAN,
            (60, line_y),
            (WINDOW_WIDTH - 60, line_y),
            2,
        )

    def _draw_help(self, surface: pygame.Surface) -> None:
        from .keybindings import key_label
        st = self.session.state
        b = self.bindings
        in_double = st in (GameState.DOUBLE_OFFERED, GameState.DOUBLE_REVEALED) or (
            st == GameState.EVALUATED and self.session.pending_prize > 0
        )
        if self._exact_mode:
            tips = [
                "Clique RANK e NAIPE",
                "CONFIRMAR para escolher",
                f"{key_label(b.get('exact_back'))}: voltar",
            ]
        elif self._reveal_active():
            tips = [
                f"{key_label(b.get('reveal_step'))}: ABRIR (passo a passo)",
                f"{key_label(b.get('reveal_fast'))}: ABRIR RAPIDO (revela tudo)",
            ]
        elif in_double:
            tips = [
                f"{key_label(b.get('double_big'))}: BIG (>7)   {key_label(b.get('double_mini'))}: MINI (<7)",
                f"{key_label(b.get('double_exact'))}: CHEIO (rank+naipe 5x/10x)",
                f"{key_label(b.get('double_start'))}: dobrar / continuar",
                f"{key_label(b.get('take_prize'))}: levar premio",
            ]
        else:
            holds = "/".join(key_label(b.get(f"hold_{i+1}")) for i in range(5))
            tips = [
                f"{holds}: HOLD nas cartas",
                f"{key_label(b.get('bet_minus'))} / {key_label(b.get('bet_plus'))} : ajusta aposta",
                f"{key_label(b.get('advance'))}: distribuir / trocar",
            ]
        if st == GameState.GAME_OVER:
            tips.append(f"{key_label(b.get('restart'))}: reiniciar")
        tips.append(f"{key_label(b.get('open_settings'))}: opcoes")
        y = WINDOW_HEIGHT - (len(tips) * (theme.FONT_SMALL_SIZE + 4)) - 10
        for line in tips:
            surf = render_text(line, theme.FONT_SMALL_SIZE, theme.FG_DIM)
            surface.blit(surf, (16, y))
            y += theme.FONT_SMALL_SIZE + 4
