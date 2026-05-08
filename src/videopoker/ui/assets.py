"""Cache de fontes e (futuros) sprites."""
from __future__ import annotations

import sys
from pathlib import Path

import pygame

from . import theme

_FONT_CACHE: dict[tuple[str, int, bool], pygame.font.Font] = {}


def _resolve_assets_dir() -> Path:
    """Localiza a pasta de assets em modo dev e quando empacotado.

    PyInstaller extrai os datas para `sys._MEIPASS` em runtime; em modo
    --onefile esse é um diretório temporário. Em desenvolvimento, sobe
    a partir de src/videopoker/ui/ até a raiz do projeto.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "assets"
    return Path(__file__).resolve().parents[3] / "assets"


ASSETS_DIR = _resolve_assets_dir()
FONTS_DIR = ASSETS_DIR / "fonts"


def get_font(size: int, *, mono: bool = False, bold: bool = False) -> pygame.font.Font:
    """Carrega fonte do cache, com fallback para SysFont caso o arquivo não exista.

    Para visual retrô, coloque "PressStart2P-Regular.ttf" em assets/fonts/.
    Sem o arquivo, usa SysFont monospace — funciona, só não fica pixelada.
    """
    key = ("default", size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    font: pygame.font.Font
    pixel_font_path = FONTS_DIR / "PressStart2P-Regular.ttf"
    vt323_path = FONTS_DIR / "VT323-Regular.ttf"

    candidate = pixel_font_path
    if mono and vt323_path.exists():
        candidate = vt323_path

    if candidate.exists():
        font = pygame.font.Font(str(candidate), size)
    else:
        # Fallback: tenta uma SysFont razoável.
        face = "monospace" if mono else "consolas,couriernew,monospace"
        font = pygame.font.SysFont(face, size, bold=bold)

    _FONT_CACHE[key] = font
    return font


def render_text(
    text: str,
    size: int,
    color: tuple[int, int, int] = theme.FG_WHITE,
    *,
    mono: bool = False,
    bold: bool = False,
) -> pygame.Surface:
    return get_font(size, mono=mono, bold=bold).render(text, True, color)
