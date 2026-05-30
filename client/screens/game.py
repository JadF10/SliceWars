import pygame
import sys
import os
import time

from client.game.fruits import (
    draw_watermelon_half, draw_apple_half,
    draw_orange_half, draw_pineapple_half,
    draw_banana_half
)

HALF_MAP = {
    "WATERMELON": draw_watermelon_half,
    "APPLE":      draw_apple_half,
    "ORANGE":     draw_orange_half,
    "PINEAPPLE":  draw_pineapple_half,
    "BANANA":     draw_banana_half,
}

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.protocol import *
from client.game.fruits    import (
    draw_fruit,
    draw_watermelon_half, draw_apple_half,
    draw_orange_half, draw_pineapple_half,
    draw_banana_half
)
from client.game.items     import draw_item
from client.game.blade     import BladeTrail, draw_cursor
from client.game.particles import ParticleSystem, get_fruit_color
from client.game.hud       import HUD, draw_combo, draw_game_over

# ─────────────────────────────────────────────
#  SliceWars Game Screen
#
#  This is the main game loop that runs during
#  an active match. It:
#  - Reads input (webcam or mouse)
#  - Sends finger coordinates to server
#  - Receives and renders game state from server
#  - Handles all visual effects locally
#
#  Architecture note (Murex signal):
#  The client NEVER trusts its own slice detection.
#  It only sends finger position to the server.
#  The server validates all slices and sends back
#  the authoritative game state.
# ─────────────────────────────────────────────

SCREEN_W = 800
SCREEN_H = 600
FPS      = 60

# Background color — dark navy
BG_COLOR = (15, 15, 35)

# Screen shake parameters
SHAKE_DECAY    = 0.85
SHAKE_DURATION = 15   # frames


class SlicedHalf:
    def __init__(self, item_type, x, y, direction):
        self.type      = item_type
        self.x         = float(x)
        self.y         = float(y)
        self.vx        = 4.0 * direction  # left=-1, right=1
        self.vy        = -3.0
        self.gravity   = 0.3
        self.lifetime  = 40  # frames
        self.direction = direction

    def update(self):
        self.vy       += self.gravity
        self.x        += self.vx
        self.y        += self.vy
        self.lifetime -= 1

    def is_dead(self):
        return self.lifetime <= 0


HALF_MAP = {
    "WATERMELON": draw_watermelon_half,
    "APPLE":      draw_apple_half,
    "ORANGE":     draw_orange_half,
    "PINEAPPLE":  draw_pineapple_half,
    "BANANA":     draw_banana_half,
}


class GameScreen:
    def __init__(self, screen, net, username, mode, input_handler):
        """
        screen        : pygame display surface
        net           : NetworkClient instance
        username      : this player's username
        mode          : MODE_SOLO / MODE_COOP / MODE_VERSUS
        input_handler : GestureClassifier or MouseInput instance
        """
        self.screen        = screen
        self.net           = net
        self.username      = username
        self.mode          = mode
        self.input         = input_handler

        # Game state — received from server each tick
        self.game_state    = {
            "scores" : {username: 0},
            "lives"  : {username: 3},
            "items"  : [],
            "fingers": {},
            "mode"   : mode,
        }

        # Local visual state
        self.blade         = BladeTrail()
        self.particles     = ParticleSystem()
        self.hud           = HUD()
        self.combo         = 1
        self.combo_timer   = 0
        self.sliced_halves = []

        # Screen shake state (triggered by mega bomb)
        self.shake_frames  = 0
        self.shake_offset  = (0, 0)

        # Track which items were alive last frame
        # so we can trigger particles when one disappears
        self.prev_item_ids = set()
        self.prev_items_by_id = {}
        self.sliced_halves = []

        # Result — set when game ends
        self.result        = None
        self.running       = True

        # Register network callbacks
        self._register_callbacks()

        # Clock
        self.clock = pygame.time.Clock()

    # ─────────────────────────────────────────
    #  Network callbacks
    # ─────────────────────────────────────────
    def _register_callbacks(self):
        if self.net:
            self.net.on(MSG_GAME_STATE, self._on_game_state)
            self.net.on(MSG_GAME_OVER,  self._on_game_over)
            self.net.on(MSG_ERROR,      self._on_error)

    def _on_game_state(self, payload: dict, server_time: int):
        """Receive authoritative game state from server."""
        self.game_state = payload

        # Detect newly sliced items by comparing item ids
        current_items = payload.get("items", [])
        current_ids = {i["id"] for i in current_items}
        sliced_ids  = self.prev_item_ids - current_ids

        for item_id in sliced_ids:
            item = self.prev_items_by_id.get(item_id)
            if item:
                # Item was just sliced — spawn particles
                color = get_fruit_color(item["type"])
                self.particles.emit(
                    int(item["x"]), int(item["y"]),
                    color, count=14
                )
                self.sliced_halves.append(
                    SlicedHalf(item["type"], item["x"], item["y"], -1)
                )
                self.sliced_halves.append(
                    SlicedHalf(item["type"], item["x"], item["y"],  1)
                )
                # Update combo
                self.combo      += 1
                self.combo_timer = FPS * 2   # 2 second combo window

                # Mega bomb hit — screen shake
                if item["type"] == ITEM_MEGA_BOMB:
                    self.shake_frames = SHAKE_DURATION

        self.prev_item_ids = current_ids
        self.prev_items_by_id = {i["id"]: i for i in current_items}

    def _on_game_over(self, payload: dict, server_time: int):
        """Game ended — store result and stop loop."""
        self.result  = payload
        self.running = False

    def _on_error(self, payload: dict, server_time: int):
        print(f"Server error: {payload.get('reason')}")
        self.running = False

    # ─────────────────────────────────────────
    #  Main game loop
    # ─────────────────────────────────────────
    def run(self):
        """
        Main loop — runs at FPS.
        1. Read input
        2. Send to server
        3. Render server state
        """
        while self.running:
            dt = self.clock.tick(FPS)

            # ── Events ─────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False

            # ── Read input ─────────────────────
            if hasattr(self.input, 'update'):
                if hasattr(self.input, 'cap'):
                    # Webcam input
                    nx, ny, gesture, latency = self.input.update()
                else:
                    # Mouse input
                    nx, ny, gesture, latency = self.input.update(
                        screen_w=SCREEN_W, screen_h=SCREEN_H
                    )
            else:
                nx, ny, gesture, latency = 0.0, 0.0, GESTURE_NONE, 0

            # Convert normalized coords to pixel coords
            px = int(nx * SCREEN_W)
            py = int(ny * SCREEN_H)

            # ── Send to server ──────────────────
            if self.net and self.net.connected:
                self.net.send_finger(nx, ny, gesture)
            self.game_state["gesture"] = gesture

            # ── Update local visuals ────────────
            self.blade.update(px, py)
            self.particles.update()

            # Update combo timer
            if self.combo_timer > 0:
                self.combo_timer -= 1
            else:
                self.combo = 1

            # Update screen shake
            if self.shake_frames > 0:
                self.shake_frames -= 1
                import random
                intensity = self.shake_frames * 0.5
                self.shake_offset = (
                    int(random.uniform(-intensity, intensity)),
                    int(random.uniform(-intensity, intensity))
                )
            else:
                self.shake_offset = (0, 0)

            # ── Render ──────────────────────────
            self._render(px, py, gesture)

        return self.result

    # ─────────────────────────────────────────
    #  Rendering
    # ─────────────────────────────────────────
    def _render(self, px: int, py: int, gesture: str):
        # Apply screen shake offset
        ox, oy = self.shake_offset

        # Fill background
        self.screen.fill(BG_COLOR)

        # ── Draw items from server state ───────
        SPECIAL_ITEMS = {ITEM_BOMB, ITEM_MEGA_BOMB, ITEM_STAR_FRUIT, ITEM_MAGNET}
        for item_dict in self.game_state.get("items", []):
            if item_dict.get("alive", True):
                shifted = dict(item_dict)
                shifted["x"] = item_dict["x"] + ox
                shifted["y"] = item_dict["y"] + oy
                if shifted["type"] in SPECIAL_ITEMS:
                    draw_item(self.screen, shifted)
                else:
                    draw_fruit(self.screen, shifted)

        # ── Draw opponent finger (versus mode) ──
        for half in self.sliced_halves:
            half.update()

        for half in self.sliced_halves:
            fn = HALF_MAP.get(half.type)
            if fn:
                fn(
                    self.screen,
                    int(half.x), int(half.y),
                    30,
                    "left" if half.direction < 0 else "right"
                )

        self.sliced_halves = [
            half for half in self.sliced_halves
            if not half.is_dead()
        ]

        if self.mode == MODE_VERSUS:
            fingers = self.game_state.get("fingers", {})
            for uname, fdata in fingers.items():
                if uname != self.username:
                    opx = int(fdata.get("x", 0) * SCREEN_W)
                    opy = int(fdata.get("y", 0) * SCREEN_H)
                    pygame.draw.circle(
                        self.screen, (255, 100, 100),
                        (opx, opy), 8, 2
                    )

        # ── Draw particles ──────────────────────
        self.particles.draw(self.screen)

        # ── Draw blade trail ───────────────────
        self.blade.draw(self.screen)
        draw_cursor(self.screen, px, py, gesture)

        # ── Draw HUD ───────────────────────────
        latency = self.net.latency_ms if self.net else 0
        self.hud.draw(
            self.screen,
            self.game_state,
            self.username,
            latency
        )

        # ── Draw combo ─────────────────────────
        if self.combo > 1:
            draw_combo(self.screen, self.combo)

       
        for half in self.sliced_halves:
            half.update()
            fn = HALF_MAP.get(half.type)
            if fn:
                fn(self.screen, int(half.x), int(half.y),
                   30, "left" if half.direction < 0 else "right")
        self.sliced_halves = [h for h in self.sliced_halves
                              if not h.is_dead()]

        pygame.display.flip()


# ─────────────────────────────────────────────
#  Offline single player test
#  Run this file directly to test the game
#  without a server using mouse input
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import random

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("SliceWars — Offline Test")

    # Use mouse input for offline test
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from client.input.webcam import MouseInput

    mouse = MouseInput()
    mouse.start()

    # Create game screen with no network
    game = GameScreen(
        screen       = screen,
        net          = None,
        username     = "Jad",
        mode         = MODE_SOLO,
        input_handler= mouse
    )

    # Inject mock fruits so we can see something
    mock_items = []
    fruit_types = [ITEM_WATERMELON, ITEM_APPLE, ITEM_ORANGE,
                   ITEM_PINEAPPLE, ITEM_BANANA]
    for i, ftype in enumerate(fruit_types):
        mock_items.append({
            "id"   : i,
            "type" : ftype,
            "x"    : 100 + i * 140,
            "y"    : 300,
            "vx"   : 0,
            "vy"   : 0,
            "alive": True
        })

    # Add a bomb and mega bomb
    mock_items.append({
        "id": 10, "type": ITEM_BOMB,
        "x": 200, "y": 200, "vx": 0, "vy": 0, "alive": True
    })
    mock_items.append({
        "id": 11, "type": ITEM_MEGA_BOMB,
        "x": 400, "y": 200, "vx": 0, "vy": 0, "alive": True
    })
    mock_items.append({
        "id": 12, "type": ITEM_STAR_FRUIT,
        "x": 600, "y": 200, "vx": 0, "vy": 0, "alive": True
    })

    game.game_state = {
        "scores" : {"Jad": 0},
        "lives"  : {"Jad": 3},
        "items"  : mock_items,
        "fingers": {},
        "mode"   : MODE_SOLO,
    }

    print("Offline test — move mouse over fruits to see effects")
    print("Press ESC to quit")

    result = game.run()
    print(f"Game ended. Result: {result}")

    mouse.stop()
    pygame.quit()
    sys.exit()
