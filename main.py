import pygame
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.protocol import *
from client.network.client       import NetworkClient
from client.input.webcam         import create_input
from client.screens.input_select import run as run_input_select
from client.screens.pre_lobby    import run as run_pre_lobby
from client.screens.lobby        import run as run_lobby
from client.screens.game_room    import run as run_game_room
from client.screens.game         import GameScreen
from client.screens.results      import run as run_results

# ─────────────────────────────────────────────
#  SliceWars — Main Entry Point
#
#  Screen flow:
#  1. Connect to server
#  2. Pre-lobby  → enter username
#  3. Input select → webcam or mouse
#  4. Lobby      → see players, chat, invite
#  5. Game room  → mode select, ready up
#  6. Game       → play the match
#  7. Results    → winner, rematch or lobby
# ─────────────────────────────────────────────

SCREEN_W    = 800
SCREEN_H    = 600
SERVER_HOST = "127.0.0.1"   # change to public IP for internet play
SERVER_PORT = 5555


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("SliceWars")

    # ── Step 1: Connect to server ──────────────
    net = NetworkClient(host=SERVER_HOST, port=SERVER_PORT)
    if not net.connect():
        _show_error(screen,
                    f"Cannot connect to server at {SERVER_HOST}:{SERVER_PORT}")
        pygame.quit()
        sys.exit()

    print(f"Connected to {SERVER_HOST}:{SERVER_PORT}")

    # ── Step 2: Pre-lobby — username first ─────
    username = run_pre_lobby(net, screen)
    if not username:
        net.disconnect()
        pygame.quit()
        sys.exit()

    print(f"Logged in as: {username}")

    # ── Step 3: Input select ───────────────────
    input_choice = run_input_select(screen)
    if not input_choice:
        net.disconnect()
        pygame.quit()
        sys.exit()

    print(f"Input method: {input_choice}")

    inp = create_input(input_choice)
    if not inp.start():
        print("ERROR: Could not start input device.")
        net.disconnect()
        pygame.quit()
        sys.exit()

    # ── Main game loop ─────────────────────────
    while True:

        # ── Step 4: Lobby ──────────────────────
        lobby_result = run_lobby(screen, net, username)
        if not lobby_result:
            break

        mode    = lobby_result.get("mode")
        room_id = lobby_result.get("room_id")
        players = lobby_result.get("players", [username])

        # ── SOLO MODE ──────────────────────────
        if mode == "SOLO":
            _play_solo(screen, net, username, inp)
            continue

        # ── MULTIPLAYER MODE ───────────────────
        mode = run_game_room(screen, net, username, room_id, players)
        if not mode:
            continue

        print(f"Starting game — mode: {mode}")
        _play_multiplayer(screen, net, username, mode,
                          room_id, players, inp)

    # ── Cleanup ────────────────────────────────
    print("Shutting down...")
    net.disconnect()
    inp.stop()
    pygame.quit()
    sys.exit()


# ─────────────────────────────────────────────
#  Solo game flow
# ─────────────────────────────────────────────
def _play_solo(screen, net, username, inp):
    net.send(build_message("SOLO_START", {}))
    time.sleep(0.5)

    while True:
        game = GameScreen(
            screen        = screen,
            net           = net,
            username      = username,
            mode          = MODE_SOLO,
            input_handler = inp
        )
        game_result = game.run()

        if not game_result:
            break

        # Fill in missing fields for results screen
        game_result.setdefault("players",     [username])
        game_result.setdefault("leaderboard", [])
        game_result.setdefault("mode",        MODE_SOLO)
        game_result.setdefault("scores",      {username: 0})
        game_result.setdefault("lives",       {username: 0})
        game_result.setdefault("winner",      username)

        action = run_results(screen, net, username, game_result)

        if action == "rematch":
            # Start a fresh solo game
            net.send(build_message("SOLO_START", {}))
            time.sleep(0.5)
            continue
        else:
            # Back to lobby
            break


# ─────────────────────────────────────────────
#  Multiplayer game flow
# ─────────────────────────────────────────────
def _play_multiplayer(screen, net, username, mode,
                      room_id, players, inp):
    while True:
        game = GameScreen(
            screen        = screen,
            net           = net,
            username      = username,
            mode          = mode,
            input_handler = inp
        )
        game_result = game.run()

        if not game_result:
            break

        # Fill in missing fields for results screen
        game_result.setdefault("players",     players)
        game_result.setdefault("leaderboard", [])
        game_result.setdefault("mode",        mode)
        game_result.setdefault("scores",      {})
        game_result.setdefault("lives",       {})

        action = run_results(screen, net, username, game_result)

        if action == "rematch":
            # Go back to game room for same players to ready up again
            new_mode = run_game_room(
                screen, net, username, room_id, players
            )
            if new_mode:
                mode = new_mode
                continue
            else:
                break
        else:
            # Back to lobby
            break


# ─────────────────────────────────────────────
#  Error screen
# ─────────────────────────────────────────────
def _show_error(screen, message: str):
    font_big   = pygame.font.SysFont(None, 40)
    font_small = pygame.font.SysFont(None, 28)
    screen.fill((20, 20, 40))

    t1 = font_big.render("Cannot connect to server", True, (255, 80, 80))
    t2 = font_small.render(message, True, (180, 180, 180))
    t3 = font_small.render("Make sure server is running, then restart.",
                            True, (180, 180, 180))
    t4 = font_small.render("Press any key to exit.", True, (120, 120, 120))

    screen.blit(t1, t1.get_rect(center=(SCREEN_W // 2, 220)))
    screen.blit(t2, t2.get_rect(center=(SCREEN_W // 2, 290)))
    screen.blit(t3, t3.get_rect(center=(SCREEN_W // 2, 330)))
    screen.blit(t4, t4.get_rect(center=(SCREEN_W // 2, 400)))
    pygame.display.flip()

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type in (pygame.QUIT,
                              pygame.KEYDOWN,
                              pygame.MOUSEBUTTONDOWN):
                waiting = False


if __name__ == "__main__":
    main()