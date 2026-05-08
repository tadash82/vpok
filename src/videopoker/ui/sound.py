"""Geração e reprodução de sons (sem assets externos).

Tons são gerados programaticamente como ondas sinoidais com decaimento
exponencial e harmônicas — soa metálico/arcade. Sem numpy, usamos
`array.array` em Python puro, o que é rápido o bastante para clipes
curtos (< 1 s).
"""
from __future__ import annotations

import array
import math

import pygame


SAMPLE_RATE = 22050
MAX_INT16 = 32767


def _generate_tone(
    frequency: float,
    duration: float,
    *,
    amplitude: float = 0.4,
    decay: float = 4.0,
    harmonics: tuple[tuple[float, float], ...] = (),
    attack: float = 0.005,
) -> bytes:
    """Gera bytes int16 estéreo de uma onda com envelope exponencial.

    - frequency: Hz da fundamental
    - duration: segundos
    - amplitude: 0..1
    - decay: maior valor = decai mais rápido
    - harmonics: tuplas (freq_relativa, amplitude_relativa)
    - attack: rampa de ataque em segundos (evita estalos)
    """
    n_samples = max(1, int(SAMPLE_RATE * duration))
    attack_samples = max(1, int(SAMPLE_RATE * attack))
    arr = array.array("h")

    two_pi_f = 2 * math.pi * frequency
    for i in range(n_samples):
        t = i / SAMPLE_RATE

        env_decay = math.exp(-decay * t / duration) if decay > 0 else 1.0
        env_attack = min(1.0, i / attack_samples) if i < attack_samples else 1.0
        env = env_decay * env_attack

        v = math.sin(two_pi_f * t)
        for hf, ha in harmonics:
            v += ha * math.sin(two_pi_f * hf * t)
        v *= amplitude * env

        sample = int(v * MAX_INT16)
        if sample > MAX_INT16:
            sample = MAX_INT16
        elif sample < -MAX_INT16:
            sample = -MAX_INT16
        # Estéreo: mesmo sample em ambos os canais
        arr.append(sample)
        arr.append(sample)

    return arr.tobytes()


def _concat_tones(*tones: bytes) -> bytes:
    return b"".join(tones)


class SoundManager:
    """Gerencia inicialização do mixer e reprodução de tons sintéticos."""

    def __init__(self) -> None:
        self._enabled = False
        try:
            pygame.mixer.pre_init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            self._enabled = True
        except Exception:
            return

        self._cache: dict[str, pygame.mixer.Sound] = {}
        self._build_static_sounds()

    # ---- construção dos clipes ----
    def _make_sound(self, key: str, raw: bytes) -> None:
        if not self._enabled:
            return
        try:
            self._cache[key] = pygame.mixer.Sound(buffer=raw)
        except Exception:
            pass

    def _build_static_sounds(self) -> None:
        # WIN POKER: arpegio ascendente C-E-G-C (alegre)
        win = _concat_tones(
            _generate_tone(523.25, 0.10, amplitude=0.35, decay=2.0, harmonics=((2.0, 0.3),)),  # C5
            _generate_tone(659.25, 0.10, amplitude=0.35, decay=2.0, harmonics=((2.0, 0.3),)),  # E5
            _generate_tone(783.99, 0.10, amplitude=0.35, decay=2.0, harmonics=((2.0, 0.3),)),  # G5
            _generate_tone(1046.5, 0.30, amplitude=0.40, decay=2.5, harmonics=((2.0, 0.25), (3.0, 0.1))),  # C6
        )
        self._make_sound("win", win)

        # LOSE: dois tons descendentes
        lose = _concat_tones(
            _generate_tone(220.0, 0.18, amplitude=0.30, decay=2.5),
            _generate_tone(165.0, 0.30, amplitude=0.30, decay=3.0),
        )
        self._make_sound("lose", lose)

        # DOBRA OFERECIDA: bling de aviso (dois tons curtos)
        offered = _concat_tones(
            _generate_tone(880.0, 0.08, amplitude=0.30, decay=3.0),
            _generate_tone(1318.5, 0.18, amplitude=0.32, decay=2.5, harmonics=((2.0, 0.2),)),
        )
        self._make_sound("double_offered", offered)

        # CARTA REVELADA na dobra (tom curto neutro antes de saber resultado)
        reveal = _generate_tone(660.0, 0.08, amplitude=0.25, decay=4.0)
        self._make_sound("reveal", reveal)

        # EMPATE (tie): sino baixo curto sem progressão
        tie = _generate_tone(440.0, 0.25, amplitude=0.30, decay=3.0, harmonics=((2.0, 0.3), (3.0, 0.1)))
        self._make_sound("tie", tie)

        # LEVAR PRÊMIO: tinido caixa-registradora simples
        take = _concat_tones(
            _generate_tone(880.0, 0.08, amplitude=0.30, decay=3.0),
            _generate_tone(1108.7, 0.20, amplitude=0.32, decay=2.5, harmonics=((2.0, 0.25),)),
        )
        self._make_sound("take", take)

        # CLICK: estalo curto agudo
        click = _generate_tone(1500.0, 0.04, amplitude=0.18, decay=10.0)
        self._make_sound("click", click)

    # ---- reprodução ----
    def play(self, key: str) -> None:
        if not self._enabled:
            return
        s = self._cache.get(key)
        if s is not None:
            s.play()

    def play_bell(self, level: int = 0) -> None:
        """Sino com pitch crescente conforme `level` aumenta.

        Cada acerto consecutivo na dobra incrementa o nível em 1 — frequência
        sobe ~3 semitons por nível, ficando "mais fino" como pediu o usuário.
        Cap em 12 níveis para não passar de ~5 kHz.
        """
        if not self._enabled:
            return
        level = max(0, min(level, 12))
        # Base C5 (523Hz). Cada nível sobe 3 semitons.
        base = 523.25
        freq = base * (2 ** (level * 3 / 12))
        # Sino: fundamental + harmônicas inarmônicas (timbre metálico)
        raw = _generate_tone(
            freq,
            0.45,
            amplitude=0.38,
            decay=3.5,
            harmonics=((2.0, 0.5), (2.76, 0.25), (5.4, 0.1)),
        )
        try:
            sound = pygame.mixer.Sound(buffer=raw)
            sound.play()
        except Exception:
            pass

    def stop_all(self) -> None:
        if self._enabled:
            pygame.mixer.stop()
