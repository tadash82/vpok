"""Mapeamento configurável de ações → teclas com persistência em JSON.

As ações são identificadas por nomes simbólicos. Cada ação tem uma tecla
padrão; o jogador pode rebindar e a configuração é salva em
~/.config/videopoker/keybindings.json (ou %APPDATA% no Windows).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pygame


# ---- Catálogo de ações ----
# Nome interno → label exibido na tela de configuração
ACTIONS: dict[str, str] = {
    "advance": "DISTRIBUIR / TROCAR / PROXIMA",
    "hold_1": "HOLD CARTA 1",
    "hold_2": "HOLD CARTA 2",
    "hold_3": "HOLD CARTA 3",
    "hold_4": "HOLD CARTA 4",
    "hold_5": "HOLD CARTA 5",
    "bet_plus": "+ APOSTA",
    "bet_minus": "- APOSTA",
    "double_start": "DOBRAR / CONTINUAR",
    "double_big": "BIG (>7)",
    "double_mini": "MINI (<7)",
    "double_exact": "CHEIO",
    "reveal_step": "ABRIR CARTA (PASSO A PASSO)",
    "reveal_fast": "ABRIR CARTA RAPIDO",
    "take_prize": "LEVAR PREMIO",
    "exact_back": "VOLTAR DO CHEIO",
    "restart": "REINICIAR APOS GAME OVER",
    "open_settings": "ABRIR OPCOES",
    "toggle_fullscreen": "TELA CHEIA / JANELA",
}

# Padrões iniciais (usando códigos pygame)
DEFAULT_BINDINGS: dict[str, int] = {
    "advance": pygame.K_RETURN,
    "hold_1": pygame.K_1,
    "hold_2": pygame.K_2,
    "hold_3": pygame.K_3,
    "hold_4": pygame.K_4,
    "hold_5": pygame.K_5,
    "bet_plus": pygame.K_EQUALS,
    "bet_minus": pygame.K_MINUS,
    "double_start": pygame.K_d,
    "double_big": pygame.K_b,
    "double_mini": pygame.K_m,
    "double_exact": pygame.K_c,
    "reveal_step": pygame.K_UP,    # subir a carta passo a passo
    "reveal_fast": pygame.K_a,     # "abrir" tudo
    "take_prize": pygame.K_l,
    "exact_back": pygame.K_BACKSPACE,
    "restart": pygame.K_r,
    "open_settings": pygame.K_F2,
    "toggle_fullscreen": pygame.K_F11,
}


def _config_path() -> Path:
    """Diretório de config segundo XDG (Linux/macOS) ou APPDATA (Windows)."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "videopoker" / "keybindings.json"


def key_label(key_code: int) -> str:
    """Nome legível da tecla (ex.: K_RETURN → 'ENTER')."""
    raw = pygame.key.name(key_code) if key_code else ""
    return raw.upper() if raw else "—"


@dataclass
class KeyBindings:
    bindings: dict[str, int]

    @classmethod
    def load(cls) -> "KeyBindings":
        path = _config_path()
        merged = dict(DEFAULT_BINDINGS)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for action, code in data.items():
                    if action in DEFAULT_BINDINGS and isinstance(code, int):
                        merged[action] = code
            except (OSError, json.JSONDecodeError):
                pass
        return cls(bindings=merged)

    def save(self) -> None:
        path = _config_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self.bindings, indent=2, sort_keys=True), encoding="utf-8"
            )
        except OSError:
            pass

    def reset_to_defaults(self) -> None:
        self.bindings = dict(DEFAULT_BINDINGS)

    def get(self, action: str) -> int:
        return self.bindings.get(action, DEFAULT_BINDINGS.get(action, 0))

    def set(self, action: str, key_code: int) -> None:
        if action in DEFAULT_BINDINGS:
            self.bindings[action] = key_code

    def action_for_key(self, key_code: int) -> str | None:
        """Retorna o nome da ação ligada a essa tecla (ou None)."""
        for action, code in self.bindings.items():
            if code == key_code:
                return action
        return None
