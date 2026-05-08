"""Gera o ícone do Video Poker (assets/icon.ico + icon.png).

Roda uma vez para criar os arquivos. PyInstaller usa o .ico no Windows;
no Linux o ícone fica embutido nos metadados (alguns DEs leem).

Uso:
    python3 scripts/make_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SIZE = 256  # base de alta resolução; PIL escala pras variações do .ico

# Paleta combinando com o tema arcade do jogo
BG_DARK = (10, 6, 26, 255)
NEON_MAGENTA = (255, 0, 200, 255)
NEON_CYAN = (0, 220, 255, 255)
CARD_FACE = (244, 236, 216, 255)
CARD_SHADOW = (50, 0, 80, 255)
SUIT_BLACK = (16, 16, 24, 255)
SUIT_RED = (220, 30, 60, 255)


def _draw_spade(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color) -> None:
    """Espade simétrico: dois círculos no topo + triângulo embaixo + base."""
    r = size // 4
    # Lóbulos superiores (dois círculos sobrepostos)
    draw.ellipse((cx - r * 2, cy - r * 2, cx, cy), fill=color)
    draw.ellipse((cx, cy - r * 2, cx + r * 2, cy), fill=color)
    # Triângulo conectando os lóbulos com a ponta inferior
    draw.polygon(
        [(cx - r * 2 + 2, cy - r), (cx + r * 2 - 2, cy - r), (cx, cy + r * 2)],
        fill=color,
    )
    # Base (haste do espade)
    base_w = r
    base_h = r // 2
    draw.polygon(
        [
            (cx - base_w, cy + r * 2 + base_h),
            (cx + base_w, cy + r * 2 + base_h),
            (cx + base_w // 2, cy + r * 2 - 2),
            (cx - base_w // 2, cy + r * 2 - 2),
        ],
        fill=color,
    )


def _draw_heart(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color) -> None:
    r = size // 4
    draw.ellipse((cx - r * 2, cy - r * 2, cx, cy), fill=color)
    draw.ellipse((cx, cy - r * 2, cx + r * 2, cy), fill=color)
    draw.polygon(
        [(cx - r * 2 + 2, cy - r // 2), (cx + r * 2 - 2, cy - r // 2), (cx, cy + r * 2)],
        fill=color,
    )


def _glow_border(img: Image.Image, color, width: int = 6) -> None:
    """Desenha borda neon com leve "halo" externo."""
    d = ImageDraw.Draw(img, "RGBA")
    # Halo externo (cor com alpha menor)
    halo = (*color[:3], 80)
    d.rectangle((0, 0, SIZE - 1, SIZE - 1), outline=halo, width=width + 6)
    d.rectangle((2, 2, SIZE - 3, SIZE - 3), outline=halo, width=width + 3)
    # Linha principal
    d.rectangle((4, 4, SIZE - 5, SIZE - 5), outline=color, width=width)


def make_icon() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), BG_DARK)
    d = ImageDraw.Draw(img, "RGBA")

    # Linhas diagonais sutis no fundo (textura CRT)
    for i in range(-SIZE, SIZE, 12):
        d.line([(i, 0), (i + SIZE, SIZE)], fill=(40, 20, 60, 90), width=1)

    # Cartas sobrepostas em leque (3 cartas → simboliza Video Poker)
    card_w, card_h = 110, 150
    cx = SIZE // 2
    cy = SIZE // 2 + 6

    # Carta de fundo (esquerda) — leve sombra/rotação simulada por offset
    bg_left = Image.new("RGBA", (card_w, card_h), CARD_FACE)
    dd = ImageDraw.Draw(bg_left)
    dd.rectangle((0, 0, card_w - 1, card_h - 1), outline=NEON_CYAN, width=4)
    bg_left = bg_left.rotate(-18, resample=Image.BICUBIC, expand=True)
    img.paste(bg_left, (cx - card_w + 4, cy - card_h // 2 - 8), bg_left)

    # Carta de fundo (direita)
    bg_right = Image.new("RGBA", (card_w, card_h), CARD_FACE)
    dd = ImageDraw.Draw(bg_right)
    dd.rectangle((0, 0, card_w - 1, card_h - 1), outline=NEON_CYAN, width=4)
    _draw_heart(dd, card_w // 2, card_h // 2, 60, SUIT_RED)
    bg_right = bg_right.rotate(18, resample=Image.BICUBIC, expand=True)
    img.paste(bg_right, (cx - 6, cy - card_h // 2 - 8), bg_right)

    # Carta principal (centro, frente) — Ás de Espadas
    front = Image.new("RGBA", (card_w, card_h), CARD_FACE)
    dd = ImageDraw.Draw(front)
    dd.rectangle((0, 0, card_w - 1, card_h - 1), outline=NEON_MAGENTA, width=5)
    # Ás no canto superior esquerdo
    try:
        from PIL import ImageFont
        try:
            font = ImageFont.truetype(
                str(ROOT / "assets" / "fonts" / "PressStart2P-Regular.ttf"), 22
            )
        except OSError:
            font = ImageFont.load_default()
        dd.text((10, 6), "A", font=font, fill=SUIT_BLACK)
    except Exception:
        dd.text((10, 6), "A", fill=SUIT_BLACK)
    # Espade central
    _draw_spade(dd, card_w // 2, card_h // 2 + 8, 70, SUIT_BLACK)
    img.paste(front, (cx - card_w // 2, cy - card_h // 2), front)

    # Borda neon ao redor de tudo
    _glow_border(img, NEON_MAGENTA, width=4)

    return img


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = make_icon()
    png_path = ASSETS / "icon.png"
    ico_path = ASSETS / "icon.ico"
    icon.save(png_path, format="PNG")
    # ICO multi-resolução: Windows usa o tamanho que combinar com cada contexto
    # (taskbar pequena, área de trabalho, dialogs, etc).
    icon.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Salvo: {png_path}")
    print(f"Salvo: {ico_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
