"""Desenha naipes (♥ ♦ ♣ ♠) como formas vetoriais preenchidas.

Mais nítido que renderizar glifos Unicode na fonte pixelada — os símbolos
ficam grandes, sólidos e legíveis em qualquer tamanho.
"""
from __future__ import annotations

import math

import pygame

from ...domain.card import Suit


def draw_suit(surface: pygame.Surface, suit: Suit, rect: pygame.Rect, color: tuple[int, int, int]) -> None:
    """Desenha o naipe centralizado dentro de `rect`."""
    if suit is Suit.HEARTS:
        _draw_heart(surface, rect, color)
    elif suit is Suit.DIAMONDS:
        _draw_diamond(surface, rect, color)
    elif suit is Suit.CLUBS:
        _draw_club(surface, rect, color)
    elif suit is Suit.SPADES:
        _draw_spade(surface, rect, color)


def _draw_heart(surface: pygame.Surface, rect: pygame.Rect, color) -> None:
    """Coração: dois círculos no topo + triângulo apontando pra baixo."""
    cx, cy = rect.centerx, rect.centery
    w = rect.width
    h = rect.height

    # Raio dos lóbulos superiores
    r = w // 4
    # Centros dos dois círculos
    left_x = cx - r
    right_x = cx + r
    top_y = cy - h // 4

    pygame.draw.circle(surface, color, (left_x, top_y), r)
    pygame.draw.circle(surface, color, (right_x, top_y), r)

    # Triângulo inferior — pontas conectam à parte de baixo dos círculos
    bottom_y = cy + h // 2 - 2
    triangle = [
        (cx - 2 * r, top_y),
        (cx + 2 * r, top_y),
        (cx, bottom_y),
    ]
    pygame.draw.polygon(surface, color, triangle)


def _draw_diamond(surface: pygame.Surface, rect: pygame.Rect, color) -> None:
    """Losango: 4 pontos."""
    cx, cy = rect.centerx, rect.centery
    half_w = rect.width // 2 - 1
    half_h = rect.height // 2 - 1
    pts = [
        (cx, cy - half_h),
        (cx + half_w, cy),
        (cx, cy + half_h),
        (cx - half_w, cy),
    ]
    pygame.draw.polygon(surface, color, pts)


def _draw_club(surface: pygame.Surface, rect: pygame.Rect, color) -> None:
    """Trevo: 3 círculos (esq, dir, topo) + cabo triangular."""
    cx, cy = rect.centerx, rect.centery
    r = rect.width // 4

    top_y = cy - r
    side_y = cy + r // 2
    left_x = cx - r
    right_x = cx + r

    pygame.draw.circle(surface, color, (cx, top_y), r)
    pygame.draw.circle(surface, color, (left_x, side_y), r)
    pygame.draw.circle(surface, color, (right_x, side_y), r)

    # Cabo triangular embaixo
    stem_top_y = side_y
    stem_bot_y = cy + rect.height // 2 - 2
    stem = [
        (cx - r, stem_top_y),
        (cx + r, stem_top_y),
        (cx + r // 2, stem_bot_y),
        (cx - r // 2, stem_bot_y),
    ]
    pygame.draw.polygon(surface, color, stem)


def _draw_spade(surface: pygame.Surface, rect: pygame.Rect, color) -> None:
    """Espada: coração invertido + cabo triangular embaixo."""
    cx, cy = rect.centerx, rect.centery
    w = rect.width
    h = rect.height

    r = w // 4
    left_x = cx - r
    right_x = cx + r
    bottom_y = cy + h // 4 - 2

    # Coração invertido (cor sólida): triângulo apontando pra cima + dois círculos
    top_y = cy - h // 2 + 2
    triangle = [
        (cx, top_y),
        (cx - 2 * r, bottom_y),
        (cx + 2 * r, bottom_y),
    ]
    pygame.draw.polygon(surface, color, triangle)
    pygame.draw.circle(surface, color, (left_x, bottom_y), r)
    pygame.draw.circle(surface, color, (right_x, bottom_y), r)

    # Cabo triangular embaixo
    stem_top_y = bottom_y + r - 2
    stem_bot_y = cy + h // 2 - 2
    stem = [
        (cx - r, stem_top_y),
        (cx + r, stem_top_y),
        (cx + int(r * 1.4), stem_bot_y),
        (cx - int(r * 1.4), stem_bot_y),
    ]
    pygame.draw.polygon(surface, color, stem)
