"""Painel com bevel estilo Win95 — usado para CRÉDITO, APOSTA, MENSAGEM."""
from __future__ import annotations

from dataclasses import dataclass

import pygame

from .. import theme
from ..assets import render_text


def draw_bevel(surface: pygame.Surface, rect: pygame.Rect, *, inset: bool = False) -> None:
    pygame.draw.rect(surface, theme.BG_PANEL, rect, border_radius=theme.PANEL_RADIUS)
    if inset:
        top, bottom = theme.BEVEL_DARK, theme.BEVEL_LIGHT
    else:
        top, bottom = theme.BEVEL_LIGHT, theme.BEVEL_DARK
    pygame.draw.line(surface, top, rect.topleft, rect.topright, 2)
    pygame.draw.line(surface, top, rect.topleft, rect.bottomleft, 2)
    pygame.draw.line(surface, bottom, rect.bottomleft, rect.bottomright, 2)
    pygame.draw.line(surface, bottom, rect.topright, rect.bottomright, 2)


@dataclass
class LabelPanel:
    """Painel com label fixo + valor variável (ex.: CRÉDITO 100)."""

    rect: pygame.Rect
    label: str
    value: str
    label_color: tuple[int, int, int] = theme.FG_GREEN
    value_color: tuple[int, int, int] = theme.FG_AMBER

    def draw(self, surface: pygame.Surface) -> None:
        draw_bevel(surface, self.rect, inset=True)

        label_surf = render_text(self.label, theme.FONT_SMALL_SIZE, self.label_color, bold=True)
        value_surf = render_text(str(self.value), theme.FONT_BIG_SIZE, self.value_color, bold=True)

        surface.blit(
            label_surf,
            (self.rect.left + theme.PANEL_PADDING, self.rect.top + 8),
        )
        surface.blit(
            value_surf,
            (
                self.rect.right - theme.PANEL_PADDING - value_surf.get_width(),
                self.rect.centery - value_surf.get_height() // 2 + 4,
            ),
        )


@dataclass
class MessagePanel:
    """Painel central de mensagem (BOA SORTE / GANHOU / ...)."""

    rect: pygame.Rect
    text: str = ""
    color: tuple[int, int, int] = theme.MSG_INFO

    def draw(self, surface: pygame.Surface) -> None:
        draw_bevel(surface, self.rect, inset=True)
        if not self.text:
            return
        msg = render_text(self.text, theme.FONT_BIG_SIZE, self.color, bold=True)
        surface.blit(msg, msg.get_rect(center=self.rect.center))
