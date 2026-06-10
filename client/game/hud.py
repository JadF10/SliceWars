import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pygame
from shared.protocol import MODE_SOLO, MODE_COOP, MODE_VERSUS


def clamp_lives(lives: int) -> int:
    return max(0, min(5, lives))


class HUD:
    def __init__(self):
        pygame.font.init()
        self.large_font = pygame.font.SysFont("Arial", 42, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 20)
        self.mono_font = pygame.font.SysFont("Consolas", 18)

    def draw(self, surface: pygame.Surface, game_state: dict, username: str, latency_ms: int):
        scores  = game_state.get("scores", {})
        lives   = game_state.get("lives", {})
        mode    = game_state.get("mode", MODE_SOLO)
        combo   = game_state.get("combo", 1)
        gesture = game_state.get("gesture", "NONE")

        if mode == MODE_COOP:
            # Co-op — show combined score and shared lives
            combined_score = sum(scores.values())
            shared_lives   = lives.get("shared", list(lives.values())[0] if lives else 0)
            shared_lives   = clamp_lives(shared_lives)
            self._draw_score(surface, "Team", combined_score, top_left=True)
            self._draw_lives(surface, shared_lives, top_left=True)

        else:
            # Solo or Versus — show personal score
            current_score = scores.get(username, 0)
            current_lives = lives.get(username, lives.get("shared", 0))
            current_lives = clamp_lives(current_lives)
            self._draw_score(surface, "You", current_score, top_left=True)
            self._draw_lives(surface, current_lives, top_left=True)

            if mode == MODE_VERSUS:
                opponent_name  = next(
                    (name for name in scores.keys() if name != username),
                    "Opponent"
                )
                opponent_score = scores.get(opponent_name, 0)
                opponent_lives = clamp_lives(lives.get(opponent_name, 0))
                self._draw_score(surface, opponent_name, opponent_score, top_left=False)
                self._draw_lives(surface, opponent_lives, top_left=False)

        if combo > 1:
            draw_combo(surface, combo)

        self._draw_ping(surface, latency_ms)
        self._draw_gesture(surface, gesture)

    def _draw_score(self, surface: pygame.Surface, label: str, score: int, top_left: bool = True):
        text = f"{label}: {score}"
        rendered = self.large_font.render(text, True, (255, 255, 255))
        if top_left:
            surface.blit(rendered, (20, 16))
        else:
            x = surface.get_width() - rendered.get_width() - 20
            surface.blit(rendered, (x, 16))

    def _draw_lives(self, surface: pygame.Surface, lives: int, top_left: bool = True):
        hearts = " ".join(["♥" for _ in range(lives)])
        if not hearts:
            hearts = "No lives"
        rendered = self.small_font.render(hearts, True, (220, 60, 60))
        y = 70
        if top_left:
            x = 20
        else:
            x = surface.get_width() - rendered.get_width() - 20
        surface.blit(rendered, (x, y))

    def _draw_ping(self, surface: pygame.Surface, latency_ms: int):
        ping_text = f"Ping: {latency_ms}ms"
        color = (0, 200, 0) if latency_ms < 60 else (240, 200, 0) if latency_ms <= 120 else (220, 50, 50)
        rendered = self.small_font.render(ping_text, True, color)
        x = surface.get_width() - rendered.get_width() - 20
        y = surface.get_height() - rendered.get_height() - 16
        surface.blit(rendered, (x, y))

    def _draw_gesture(self, surface: pygame.Surface, gesture: str):
        text = f"Gesture: {gesture}"
        rendered = self.mono_font.render(text, True, (180, 180, 180))
        surface.blit(rendered, (20, surface.get_height() - rendered.get_height() - 16))


def draw_combo(surface: pygame.Surface, combo: int):
    text = f"{combo}x"
    font = pygame.font.SysFont("Arial", 38, bold=True)
    rendered = font.render(text, True, (255, 215, 0))
    x = (surface.get_width() - rendered.get_width()) // 2
    surface.blit(rendered, (x, 12))


def draw_game_over(surface: pygame.Surface, winner: str):
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))
    font = pygame.font.SysFont("Arial", 60, bold=True)
    text = f"{winner} WINS!"
    rendered = font.render(text, True, (255, 255, 255))
    x = (surface.get_width() - rendered.get_width()) // 2
    y = (surface.get_height() - rendered.get_height()) // 2
    surface.blit(rendered, (x, y))


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((900, 600))
    pygame.display.set_caption("SliceWars HUD Test")
    clock = pygame.time.Clock()
    hud = HUD()

    mock_state = {
        "scores": {"Player1": 38, "Player2": 42},
        "lives": {"Player1": 3, "Player2": 4},
        "mode": MODE_VERSUS,
        "combo": 3,
        "gesture": "SLICE",
    }
    username = "Player1"
    latency_ms = 48
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                mock_state["combo"] = mock_state.get("combo", 1) + 1
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_g:
                mock_state["gesture"] = "POWER_UP" if mock_state["gesture"] == "SLICE" else "SLICE"

        screen.fill((16, 22, 42))
        hud.draw(screen, mock_state, username, latency_ms)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
