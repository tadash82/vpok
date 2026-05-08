"""Visualização da paytable (lista de combinações + multiplicador × aposta)."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from ...domain.hand_rank import HandRank
from ...domain.paytable import Paytable
from .. import theme
from ..assets import render_text
from .panel import draw_bevel


@dataclass
class PaytableView:
    rect: pygame.Rect
    paytable: Paytable
    bet: float = 0.10
    highlight: HandRank | None = None
    preview_highlight: HandRank | None = None
    elapsed: float = 0.0

    def draw(self, surface: pygame.Surface) -> None:
        draw_bevel(surface, self.rect, inset=True)

        title = render_text(
            "PAGAMENTOS", theme.FONT_NORMAL_SIZE, theme.NEON_ORANGE, bold=True
        )
        surface.blit(
            title,
            (self.rect.centerx - title.get_width() // 2, self.rect.top + 8),
        )

        y = self.rect.top + 8 + title.get_height() + 8
        line_h = theme.FONT_SMALL_SIZE + 8

        # Pulso 0..1 a ~3 Hz para o preview piscar
        pulse = 0.5 + 0.5 * math.sin(self.elapsed * 2 * math.pi * 3)

        for i, entry in enumerate(self.paytable):
            is_hl = self.highlight is not None and entry.rank is self.highlight
            is_preview = (
                not is_hl
                and self.preview_highlight is not None
                and entry.rank is self.preview_highlight
            )
            base_color = theme.PAYTABLE_PALETTE[i % len(theme.PAYTABLE_PALETTE)]

            if is_hl:
                color = theme.FG_WHITE
            elif is_preview:
                # Pisca entre branco e cor base sincronizado com o pulso
                color = _lerp_color(base_color, theme.FG_WHITE, pulse)
            else:
                color = base_color

            label = render_text(entry.label, theme.FONT_SMALL_SIZE, color, bold=True)
            payout_value = entry.multiplier * self.bet
            if payout_value == int(payout_value):
                value_str = str(int(payout_value))
            else:
                value_str = f"{payout_value:.2f}"
            value = render_text(value_str, theme.FONT_SMALL_SIZE, color, bold=True)

            row_rect = pygame.Rect(self.rect.left + 4, y - 3, self.rect.width - 8, line_h)
            if is_hl:
                pygame.draw.rect(surface, base_color, row_rect, border_radius=2)
            elif is_preview:
                # Borda pulsante destacando a linha
                pygame.draw.rect(
                    surface,
                    base_color,
                    row_rect,
                    width=max(1, int(1 + pulse * 2)),
                    border_radius=2,
                )

            surface.blit(label, (self.rect.left + 12, y))
            surface.blit(value, (self.rect.right - 12 - value.get_width(), y))

            y += line_h


def _lerp_color(a, b, t: float):
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )
