"""Cena de configuração: rebind de teclas."""
from __future__ import annotations

from typing import Callable

import pygame

from ..config import WINDOW_HEIGHT, WINDOW_WIDTH
from . import theme
from .assets import render_text
from .keybindings import ACTIONS, KeyBindings, key_label
from .widgets.button import Button
from .widgets.panel import draw_bevel


# Teclas que não podem ser usadas como binding (reservadas)
RESERVED_KEYS = {pygame.K_ESCAPE}


class SettingsScene:
    """Tela de configuração de controles.

    Lista cada ação com sua tecla atual e um botão REBIND. Ao clicar
    REBIND, a próxima tecla pressionada é gravada (exceto reservadas).
    """

    def __init__(self, bindings: KeyBindings, on_close: Callable[[], None]) -> None:
        self.bindings = bindings
        self.on_close = on_close

        self._waiting_for: str | None = None  # ação aguardando rebind
        self._error_msg: str = ""
        self._error_until: float = 0.0
        self.elapsed = 0.0

        self._scroll_offset = 0
        self._build_layout()

    def _build_layout(self) -> None:
        # Lista de ações: cada linha é uma row (label, tecla, botão REBIND)
        self.row_buttons: list[tuple[str, Button]] = []
        list_top = 88
        row_h = 22
        row_pad = 2
        rebind_w = 100

        n = len(ACTIONS)
        for i, action in enumerate(ACTIONS):
            row_y = list_top + i * (row_h + row_pad)
            btn = Button(
                rect=pygame.Rect(
                    WINDOW_WIDTH - rebind_w - 30, row_y + 2, rebind_w, row_h - 4
                ),
                label="REBIND",
                on_click=lambda a=action: self._on_rebind(a),
                size=theme.FONT_SMALL_SIZE,
            )
            self.row_buttons.append((action, btn))
        self._row_h = row_h
        self._row_pad = row_pad
        self._list_top = list_top
        list_bottom = list_top + n * (row_h + row_pad)

        # Botões inferiores: VOLTAR e RESTAURAR PADRÃO
        btn_h = 32
        btn_y = list_bottom + 10
        # Garante que não passa do limite da janela
        if btn_y + btn_h > WINDOW_HEIGHT - 20:
            btn_y = WINDOW_HEIGHT - 20 - btn_h
        self.back_btn = Button(
            rect=pygame.Rect(20, btn_y, 200, btn_h),
            label="VOLTAR",
            on_click=self.on_close,
            size=theme.FONT_NORMAL_SIZE,
        )
        self.reset_btn = Button(
            rect=pygame.Rect(WINDOW_WIDTH - 260, btn_y, 240, btn_h),
            label="RESTAURAR PADRAO",
            on_click=self._on_reset,
            size=theme.FONT_NORMAL_SIZE,
        )
        self._btn_y = btn_y

    # ---- handlers ----
    def _on_rebind(self, action: str) -> None:
        self._waiting_for = action
        self._error_msg = ""

    def _on_reset(self) -> None:
        self.bindings.reset_to_defaults()
        self.bindings.save()
        self._waiting_for = None

    def _show_error(self, msg: str) -> None:
        self._error_msg = msg
        self._error_until = self.elapsed + 2.5

    def handle_event(self, event: pygame.event.Event) -> None:
        # Captura tecla quando aguardando rebind
        if event.type == pygame.KEYDOWN and self._waiting_for is not None:
            if event.key in RESERVED_KEYS:
                self._show_error("TECLA RESERVADA")
                return
            # Verifica conflito com outra ação
            existing = self.bindings.action_for_key(event.key)
            if existing is not None and existing != self._waiting_for:
                # Limpa o conflito (a ação antiga fica sem tecla até ser
                # rebindada — mas pra evitar bagunça, troca: a outra ação
                # recebe a tecla anteriormente da que estamos editando).
                old_key = self.bindings.get(self._waiting_for)
                self.bindings.set(existing, old_key)
            self.bindings.set(self._waiting_for, event.key)
            self.bindings.save()
            self._waiting_for = None
            return

        # ESC fecha a tela (reservado)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._waiting_for = None
            self.on_close()
            return

        # Cliques nos botões
        for _, btn in self.row_buttons:
            btn.handle_event(event)
        self.back_btn.handle_event(event)
        self.reset_btn.handle_event(event)

    def update(self, dt: float) -> None:
        self.elapsed += dt
        if self._error_msg and self.elapsed > self._error_until:
            self._error_msg = ""

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DARK)

        # Título
        title = render_text(
            "OPCOES - CONTROLES",
            theme.FONT_TITLE_SIZE,
            theme.NEON_MAGENTA,
            bold=True,
        )
        surface.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 24))
        pygame.draw.line(
            surface,
            theme.NEON_CYAN,
            (60, 24 + title.get_height() + 6),
            (WINDOW_WIDTH - 60, 24 + title.get_height() + 6),
            2,
        )

        # Subtítulo / instrução
        if self._waiting_for is not None:
            label = ACTIONS[self._waiting_for]
            instr = render_text(
                f"PRESSIONE A TECLA PARA: {label}",
                theme.FONT_NORMAL_SIZE,
                theme.NEON_YELLOW,
                bold=True,
            )
        else:
            instr = render_text(
                "CLIQUE EM REBIND E PRESSIONE A NOVA TECLA",
                theme.FONT_SMALL_SIZE,
                theme.FG_DIM,
            )
        surface.blit(instr, ((WINDOW_WIDTH - instr.get_width()) // 2, 64))

        # Lista de ações
        for i, (action, btn) in enumerate(self.row_buttons):
            row_y = self._list_top + i * (self._row_h + self._row_pad)
            row_rect = pygame.Rect(20, row_y, WINDOW_WIDTH - 40, self._row_h)
            highlighted = self._waiting_for == action
            color = theme.NEON_YELLOW if highlighted else theme.BG_PANEL
            draw_bevel(surface, row_rect, inset=True)
            if highlighted:
                pygame.draw.rect(surface, theme.NEON_YELLOW, row_rect, width=2, border_radius=4)

            # Label da ação
            action_label = render_text(
                ACTIONS[action], theme.FONT_SMALL_SIZE, theme.NEON_CYAN, bold=True
            )
            surface.blit(action_label, (row_rect.left + 16, row_y + (self._row_h - action_label.get_height()) // 2))

            # Tecla atual
            current = key_label(self.bindings.get(action))
            text_color = theme.NEON_YELLOW if highlighted else theme.NEON_GREEN
            key_text = render_text(current, theme.FONT_NORMAL_SIZE, text_color, bold=True)
            key_x = WINDOW_WIDTH - 30 - 120 - 24 - key_text.get_width()
            surface.blit(key_text, (key_x, row_y + (self._row_h - key_text.get_height()) // 2))

            btn.draw(surface)

        # Mensagem de erro temporária (entre lista e botões)
        if self._error_msg:
            err = render_text(self._error_msg, theme.FONT_NORMAL_SIZE, theme.MSG_LOSE, bold=True)
            surface.blit(
                err,
                ((WINDOW_WIDTH - err.get_width()) // 2, self._btn_y - err.get_height() - 4),
            )

        # Botões inferiores
        self.back_btn.draw(surface)
        self.reset_btn.draw(surface)

        # Dica (entre os botões inferiores)
        tip = render_text(
            "ESC: voltar (reservada)",
            theme.FONT_SMALL_SIZE,
            theme.FG_DIM,
        )
        tip_x = (WINDOW_WIDTH - tip.get_width()) // 2
        tip_y = self._btn_y + (self.back_btn.rect.height - tip.get_height()) // 2
        surface.blit(tip, (tip_x, tip_y))
