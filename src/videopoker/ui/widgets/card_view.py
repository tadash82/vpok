"""Renderização de uma carta + indicador HOLD."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from ...domain.card import Card, Suit
from .. import theme
from ..assets import render_text
from .suit_drawer import draw_suit


@dataclass
class CardView:
    rect: pygame.Rect
    card: Card | None = None
    held: bool = False
    revealed: bool = True
    deal_progress: float = 1.0  # 0..1 — animação de aparecer

    def contains(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)

    def draw(self, surface: pygame.Surface, t: float) -> None:
        if self.deal_progress < 1.0:
            self._draw_dealing(surface, self.deal_progress)
            return
        if self.card is None or not self.revealed:
            self._draw_back(surface)
            return
        self._draw_face(surface, self.card)
        if self.held:
            self._draw_hold_indicator(surface, t)

    def _draw_dealing(self, surface: pygame.Surface, p: float) -> None:
        """Carta surgindo: cresce verticalmente do centro até o tamanho final."""
        h = max(2, int(self.rect.height * p))
        rect = pygame.Rect(0, 0, self.rect.width, h)
        rect.center = self.rect.center
        pygame.draw.rect(surface, theme.CARD_BACK, rect, border_radius=theme.CARD_RADIUS)
        pygame.draw.rect(
            surface, theme.NEON_MAGENTA, rect, width=2, border_radius=theme.CARD_RADIUS
        )

    # ---- internas ----
    def _draw_back(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, theme.CARD_BACK, self.rect, border_radius=theme.CARD_RADIUS)
        # padrão diagonal estilo retrô
        for i in range(-self.rect.height, self.rect.width, 8):
            pygame.draw.line(
                surface,
                theme.NEON_MAGENTA,
                (self.rect.left + max(i, 0), self.rect.top + max(-i, 0)),
                (
                    self.rect.left + min(i + self.rect.height, self.rect.width),
                    self.rect.top + min(self.rect.height, self.rect.width - i),
                ),
                1,
            )
        pygame.draw.rect(
            surface, theme.CARD_BORDER, self.rect, width=3, border_radius=theme.CARD_RADIUS
        )

    def _draw_face(self, surface: pygame.Surface, card: Card) -> None:
        pygame.draw.rect(surface, theme.CARD_FACE, self.rect, border_radius=theme.CARD_RADIUS)
        pygame.draw.rect(
            surface, theme.CARD_BORDER, self.rect, width=3, border_radius=theme.CARD_RADIUS
        )

        suit_color = theme.SUIT_RED if card.suit.color == "vermelho" else theme.SUIT_BLACK

        # Tamanhos baseados na altura da carta — escalam para mini cards também.
        is_big = self.rect.height >= 120
        rank_size = max(14, self.rect.height // 6)
        small_suit_size = max(10, self.rect.height // 9)
        big_suit_size = max(28, self.rect.height // 2)

        rank_surf = render_text(card.rank.label, rank_size, suit_color, bold=True)

        # Canto top-left: rank + naipe pequeno (vetorial)
        margin = 6 if is_big else 4
        surface.blit(rank_surf, (self.rect.left + margin, self.rect.top + margin))
        suit_rect_tl = pygame.Rect(
            self.rect.left + margin,
            self.rect.top + margin + rank_surf.get_height() + 2,
            small_suit_size,
            small_suit_size,
        )
        draw_suit(surface, card.suit, suit_rect_tl, suit_color)

        # Centro: naipe grande vetorial
        big_rect = pygame.Rect(0, 0, big_suit_size, big_suit_size)
        big_rect.center = self.rect.center
        draw_suit(surface, card.suit, big_rect, suit_color)

        # Canto bottom-right (invertido)
        rank_br = pygame.transform.rotate(rank_surf, 180)
        surface.blit(
            rank_br,
            (
                self.rect.right - margin - rank_br.get_width(),
                self.rect.bottom - margin - rank_br.get_height(),
            ),
        )
        suit_rect_br = pygame.Rect(
            self.rect.right - margin - small_suit_size,
            self.rect.bottom - margin - rank_br.get_height() - 2 - small_suit_size,
            small_suit_size,
            small_suit_size,
        )
        draw_suit(surface, card.suit, suit_rect_br, suit_color)

    def _draw_hold_indicator(self, surface: pygame.Surface, t: float) -> None:
        # Pisca a 2Hz suaves.
        pulse = 0.6 + 0.4 * math.sin(t * 6.28 * 2)
        color = tuple(int(c * pulse) for c in theme.HOLD_YELLOW)

        label = render_text("HOLD", theme.FONT_NORMAL_SIZE, theme.SUIT_BLACK, bold=True)
        pad_x, pad_y = 14, 6
        rect = pygame.Rect(0, 0, label.get_width() + pad_x * 2, label.get_height() + pad_y * 2)
        rect.midbottom = (self.rect.centerx, self.rect.top - 6)

        pygame.draw.rect(surface, color, rect, border_radius=4)
        pygame.draw.rect(surface, theme.HOLD_BORDER, rect, width=2, border_radius=4)
        surface.blit(label, label.get_rect(center=rect.center))
