import pygame
import sys
sys.path.append('.')

from client.screens.input_select import run as run_input_select
from client.screens.pre_lobby import run as run_pre_lobby
from client.screens.lobby import run as run_lobby
from client.screens.game_room import run as run_game_room
from client.screens.results import run as run_results

pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption('SliceWars')
clock = pygame.time.Clock()

# ── Screen 1: input select ──────────────────
choice = run_input_select(screen)
print(f"Input choice: {choice}")

# ── Screen 2: pre lobby (mock — no server) ──
print("Pre-lobby: skipped (needs server)")

# ── Screen 3: lobby (mock) ──────────────────
print("Lobby: skipped (needs server)")

# ── Screen 4: game room (mock) ──────────────
print("Game room: skipped (needs server)")

# ── Screen 5: results (mock data) ───────────
mock_payload = {
    "winner": "Jad",
    "scores": {"Jad": 42, "Player2": 28},
    "lives": {"Jad": 2, "Player2": 0},
    "leaderboard": [
        {"username": "Jad", "wins": 3},
        {"username": "Player2", "wins": 1},
    ]
}
result = run_results(screen, net=None, username="Jad", game_over_payload=mock_payload)
print(f"Player chose: {result}")

pygame.quit()
sys.exit()
