"""Aplicação Pygame: cria janela e conduz o game loop."""
from __future__ import annotations

import pygame

from ..config import FPS, INITIAL_CREDITS, WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH
from ..game.session import GameSession
from . import theme
from .keybindings import KeyBindings
from .settings_scene import SettingsScene
from .sound import SoundManager
from .table_scene import TableScene


class App:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)

        # Canvas lógico — toda a UI sempre desenha aqui, em 960x640.
        # A janela real pode ter qualquer tamanho; fazemos blit escalado.
        self.canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))

        self._fullscreen = False
        self._windowed_size = (WINDOW_WIDTH, WINDOW_HEIGHT)
        self.screen = pygame.display.set_mode(
            self._windowed_size, pygame.RESIZABLE
        )

        self.clock = pygame.time.Clock()
        self.running = True

        self.sound = SoundManager()
        self.bindings = KeyBindings.load()
        self.session = GameSession(initial_credits=INITIAL_CREDITS)
        self.table_scene = TableScene(
            self.session,
            sound=self.sound,
            bindings=self.bindings,
            on_open_settings=self._open_settings,
        )
        self.settings_scene: SettingsScene | None = None
        self.scene = self.table_scene

        self._scanlines = self._build_scanlines()

    def _open_settings(self) -> None:
        self.settings_scene = SettingsScene(self.bindings, on_close=self._close_settings)
        self.scene = self.settings_scene

    def _close_settings(self) -> None:
        self.settings_scene = None
        self.scene = self.table_scene

    def _build_scanlines(self) -> pygame.Surface:
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for y in range(0, WINDOW_HEIGHT, 3):
            pygame.draw.line(surf, (0, 0, 0, 40), (0, y), (WINDOW_WIDTH, y), 1)
        return surf

    def _toggle_fullscreen(self) -> None:
        self._fullscreen = not self._fullscreen
        if self._fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self._windowed_size, pygame.RESIZABLE)

    def _present(self) -> None:
        """Blita o canvas escalado no display, mantendo aspect ratio."""
        screen_w, screen_h = self.screen.get_size()
        if screen_w == WINDOW_WIDTH and screen_h == WINDOW_HEIGHT:
            self.screen.blit(self.canvas, (0, 0))
            return

        # Calcula escala mantendo aspect ratio (pillarbox/letterbox)
        sx = screen_w / WINDOW_WIDTH
        sy = screen_h / WINDOW_HEIGHT
        scale = min(sx, sy)
        target_w = int(WINDOW_WIDTH * scale)
        target_h = int(WINDOW_HEIGHT * scale)
        offset_x = (screen_w - target_w) // 2
        offset_y = (screen_h - target_h) // 2

        scaled = pygame.transform.smoothscale(self.canvas, (target_w, target_h))
        self.screen.fill((0, 0, 0))  # barras laterais pretas
        self.screen.blit(scaled, (offset_x, offset_y))

    def _translate_event(self, event: pygame.event.Event) -> pygame.event.Event:
        """Converte coordenadas do display real para coordenadas do canvas.

        Eventos de mouse precisam ser remapeados quando a tela está escalada,
        senão os botões ficam offset.
        """
        if event.type not in (
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
            pygame.MOUSEMOTION,
        ):
            return event

        screen_w, screen_h = self.screen.get_size()
        if screen_w == WINDOW_WIDTH and screen_h == WINDOW_HEIGHT:
            return event

        sx = screen_w / WINDOW_WIDTH
        sy = screen_h / WINDOW_HEIGHT
        scale = min(sx, sy)
        target_w = int(WINDOW_WIDTH * scale)
        target_h = int(WINDOW_HEIGHT * scale)
        offset_x = (screen_w - target_w) // 2
        offset_y = (screen_h - target_h) // 2

        def _to_canvas(pos):
            x = (pos[0] - offset_x) / scale
            y = (pos[1] - offset_y) / scale
            return (int(x), int(y))

        # Pygame events são imutáveis; cria novo dict e re-emite
        new_dict = {k: v for k, v in event.__dict__.items()}
        if "pos" in new_dict:
            new_dict["pos"] = _to_canvas(new_dict["pos"])
        if "rel" in new_dict:
            # rel não precisa de offset, só escala
            rx = new_dict["rel"][0] / scale
            ry = new_dict["rel"][1] / scale
            new_dict["rel"] = (int(rx), int(ry))
        return pygame.event.Event(event.type, new_dict)

    def run(self) -> None:
        toggle_key = self.bindings.get("toggle_fullscreen")
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if isinstance(self.scene, SettingsScene):
                        # SettingsScene trata ESC internamente (fecha)
                        pass
                    else:
                        self.running = False
                        continue
                if event.type == pygame.KEYDOWN and event.key == self.bindings.get(
                    "toggle_fullscreen"
                ):
                    self._toggle_fullscreen()
                    continue
                if event.type == pygame.VIDEORESIZE and not self._fullscreen:
                    # Salva último tamanho de janela para restaurar ao sair de fullscreen
                    self._windowed_size = (event.w, event.h)
                    self.screen = pygame.display.set_mode(
                        self._windowed_size, pygame.RESIZABLE
                    )
                    continue

                # Eventos para a cena: traduz coordenadas de mouse
                self.scene.handle_event(self._translate_event(event))

            self.scene.update(dt)
            self.scene.render(self.canvas)
            self.canvas.blit(self._scanlines, (0, 0))
            self._present()
            pygame.display.flip()

        pygame.quit()
