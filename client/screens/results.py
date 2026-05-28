# client/screens/results.py
# Pygame screen shown after a match ends, displaying winner, scores, lives, and leaderboard.

import pygame
from typing import Optional

try:
    from shared.protocol import MSG_GAME_OVER
except Exception:
    MSG_GAME_OVER = "GAME_OVER"

WIDTH = 800
HEIGHT = 600
BG_COLOR = (40, 40, 40)
TEXT_COLOR = (255, 255, 255)
GOLD = (212, 175, 55)
WHITE = (255, 255, 255)
GRAY = (180, 180, 180)
BUTTON_COLOR = (50, 115, 220)
BUTTON_HOVER = (70, 135, 240)
BUTTON_BG = (40, 40, 40)


def draw_text(surface, text, font, color, center):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=center)
    surface.blit(rendered, rect)


class Button:
    def __init__(self, rect, text, font):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font

    def draw(self, surface, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        color = BUTTON_HOVER if hovered else BUTTON_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        draw_text(surface, self.text, self.font, TEXT_COLOR, self.rect.center)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


def run(screen, net, username, game_over_payload):
    if screen is None:
        pygame.init()
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("SliceWars Results")

    title_font = pygame.font.SysFont(None, 56)
    section_font = pygame.font.SysFont(None, 28)
    text_font = pygame.font.SysFont(None, 22)
    button_font = pygame.font.SysFont(None, 28)

    winner = None
    mode = game_over_payload.get("mode") if isinstance(game_over_payload, dict) else None
    players = game_over_payload.get("players", []) if isinstance(game_over_payload, dict) else []
    scores = game_over_payload.get("scores", {}) if isinstance(game_over_payload, dict) else {}
    lives = game_over_payload.get("lives", {}) if isinstance(game_over_payload, dict) else {}
    leaderboard = game_over_payload.get("leaderboard", []) if isinstance(game_over_payload, dict) else []

    if isinstance(game_over_payload, dict):
        winner = game_over_payload.get("winner")

    if winner and mode == "COOP":
        title_text = "TEAM WINS!"
    elif winner:
        title_text = f"{winner} WINS!"
    else:
        title_text = "GAME OVER"

    button_rematch = Button((WIDTH // 2 - 220, HEIGHT - 100, 180, 50), "Play Again", button_font)
    button_lobby = Button((WIDTH // 2 + 40, HEIGHT - 100, 180, 50), "Back to Lobby", button_font)

    running = True
    result = None

    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif button_rematch.is_clicked(event):
                result = "rematch"
                running = False
            elif button_lobby.is_clicked(event):
                result = "lobby"
                running = False

        screen.fill(BG_COLOR)
        draw_text(screen, title_text, title_font, GOLD if winner else WHITE, (WIDTH // 2, 80))

        draw_text(screen, "Scores", section_font, WHITE, (WIDTH // 4, 150))
        draw_text(screen, "Lives", section_font, WHITE, (WIDTH // 4, 220))

        y = 185
        for player in players:
            player_score = scores.get(player, 0)
            draw_text(screen, f"{player}: {player_score}", text_font, GRAY, (WIDTH // 2.8, y),)
            y += 28

        y = 255
        for player in players:
            player_lives = lives.get(player, 0)
            draw_text(screen, f"{player}: {player_lives}", text_font, GRAY, (WIDTH // 2.8, y),)
            y += 28

        draw_text(screen, "Leaderboard", section_font, WHITE, (WIDTH * 0.75, 150))
        y = 185
        for index, entry in enumerate(leaderboard[:8], start=1):
            if isinstance(entry, dict):
                name = entry.get("username", "")
                score = entry.get("score", 0)
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                name, score = entry[0], entry[1]
            else:
                name = str(entry)
                score = ""
            draw_text(screen, f"{index}. {name} {score}", text_font, GRAY, (WIDTH * 0.75, y))
            y += 26

        button_rematch.draw(screen, mouse_pos)
        button_lobby.draw(screen, mouse_pos)

        pygame.display.flip()
        pygame.time.Clock().tick(60)

    return result


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("SliceWars Results Test")

    payload = {
        "mode": "VERSUS",
        "winner": "Player1",
        "players": ["Player1", "Player2"],
        "scores": {"Player1": 12, "Player2": 8},
        "lives": {"Player1": 2, "Player2": 0},
        "leaderboard": [
            {"username": "Player1", "score": 12},
            {"username": "Player2", "score": 8},
            {"username": "Spectator", "score": 5},
        ],
    }

    result = run(screen, None, "Player1", payload)
    print("Results returned:", result)
