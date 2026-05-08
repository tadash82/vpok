"""Botão clicável com visual retrô (bevel)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pygame

from .. import theme
from ..assets import render_text


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    on_click: Callable[[], None]
    enabled: bool = True
    hovered: bool = False
    pressed: bool = False
    size: int = field(default=theme.FONT_NORMAL_SIZE)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Retorna True se o evento foi consumido."""
        if not self.enabled:
            self.hovered = False
            self.pressed = False
            return False

        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.pressed
            self.pressed = False
            if was_pressed and self.rect.collidepoint(event.pos):
                self.on_click()
                return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        if not self.enabled:
            bg = theme.BTN_BG_DISABLED
            fg = theme.FG_DIM
        elif self.pressed:
            bg = theme.BTN_BG_ACTIVE
            fg = theme.FG_AMBER
        elif self.hovered:
            bg = theme.BTN_BG_HOVER
            fg = theme.FG_AMBER
        else:
            bg = theme.BTN_BG
            fg = theme.FG_GREEN

        pygame.draw.rect(surface, bg, self.rect, border_radius=4)
        # Bevel
        if self.pressed:
            top, bottom = theme.BEVEL_DARK, theme.BEVEL_LIGHT
        else:
            top, bottom = theme.BEVEL_LIGHT, theme.BEVEL_DARK
        pygame.draw.line(surface, top, self.rect.topleft, self.rect.topright, 2)
        pygame.draw.line(surface, top, self.rect.topleft, self.rect.bottomleft, 2)
        pygame.draw.line(surface, bottom, self.rect.bottomleft, self.rect.bottomright, 2)
        pygame.draw.line(surface, bottom, self.rect.topright, self.rect.bottomright, 2)
        pygame.draw.rect(surface, theme.BTN_BORDER, self.rect, width=1, border_radius=4)

        label = render_text(self.label, self.size, fg, bold=True)
        surface.blit(label, label.get_rect(center=self.rect.center))
