import random
import time
import math
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.protocol import *

# ─────────────────────────────────────────────
#  Game constants
# ─────────────────────────────────────────────
SCREEN_W       = 800
SCREEN_H       = 600
TICK_RATE      = 30          # server updates per second
TICK_INTERVAL  = 1.0 / TICK_RATE

LIVES_SOLO     = 3
LIVES_COOP     = 5
LIVES_VERSUS   = 3

SPAWN_INTERVAL_MIN = 0.8     # seconds between fruit spawns
SPAWN_INTERVAL_MAX = 2.0
STAR_BASE_CHANCE   = 0.005   # 0.5% per tick
MEGA_BOMB_CHANCE   = 0.001   # 0.1% per tick

SLICE_RADIUS   = 40          # pixels — hit detection radius


# ─────────────────────────────────────────────
#  Item  — represents one fruit/bomb in flight
# ─────────────────────────────────────────────
class Item:
    _id_counter = 0

    def __init__(self, item_type: str, x: float, y: float,
                 vx: float, vy: float):
        Item._id_counter += 1
        self.id        = Item._id_counter
        self.type      = item_type
        self.x         = x
        self.y         = y
        self.vx        = vx        # horizontal velocity px/tick
        self.vy        = vy        # vertical velocity px/tick
        self.gravity   = 0.4       # px/tick² downward acceleration
        self.alive     = True      # False = sliced or off-screen
        self.sliced_by = None      # username of who sliced it

    def update(self):
        """Advance physics one tick."""
        self.vy += self.gravity
        self.x  += self.vx
        self.y  += self.vy

    def is_off_screen(self) -> bool:
        return self.y > SCREEN_H + 100 or self.x < -100 or self.x > SCREEN_W + 100

    def to_dict(self) -> dict:
        return {
            "id"   : self.id,
            "type" : self.type,
            "x"    : round(self.x, 1),
            "y"    : round(self.y, 1),
            "vx"   : round(self.vx, 2),
            "vy"   : round(self.vy, 2),
            "alive": self.alive
        }


# ─────────────────────────────────────────────
#  GameRoom  — manages one match session
# ─────────────────────────────────────────────
class GameRoom:
    def __init__(self, room_id: str, players: list, server):
        self.room_id    = room_id
        self.players    = players          # list of usernames
        self.server     = server           # reference to SliceWarsServer
        self.mode       = MODE_VERSUS      # default mode
        self.active     = False
        self.spectators = set()

        # Per-player state
        self.scores = {p: 0 for p in players}
        self.lives  = {p: LIVES_SOLO for p in players}
        self.ready  = {p: False for p in players}
        self.finger = {p: (0, 0, GESTURE_NONE) for p in players}
        self.start_requested = False

        # Items currently in flight
        self.items = {}                    # item_id → Item

        # Spawn timing
        self.next_spawn_time   = 0.0
        self.last_star_time    = 0.0       # for hunger bonus calculation
        self.ticks_since_star  = 0

        # Shield state (SHIELD gesture blocks next bomb)
        self.shield_active = {p: False for p in players}

    # ─────────────────────────────────────────
    #  Setup
    # ─────────────────────────────────────────
    def set_mode(self, mode: str):
        self.mode = mode
        if mode == MODE_SOLO:
            self.lives = {p: LIVES_SOLO for p in self.players}
        elif mode == MODE_COOP:
            self.lives = {"shared": LIVES_COOP}
        elif mode == MODE_VERSUS:
            self.lives = {p: LIVES_VERSUS for p in self.players}

    def set_ready(self, username: str):
        self.ready[username] = True

    def all_ready(self) -> bool:
        return all(self.ready.values())

    def consume_start_request(self) -> bool:
        if self.start_requested or not self.all_ready():
            return False
        self.start_requested = True
        return True

    def add_spectator(self, username: str):
        self.spectators.add(username)

    # ─────────────────────────────────────────
    #  Main game loop  (runs in its own thread)
    # ─────────────────────────────────────────
    def run(self):
        self.active          = True
        self.next_spawn_time = time.time() + 1.0   # first fruit after 1 second

        while self.active:
            tick_start = time.time()

            self.update()

            # Check win/lose conditions
            if self.is_game_over():
                self.finish()
                break

            # Broadcast state to all players and spectators
            self.broadcast_state()

            # Sleep for remainder of tick
            elapsed = time.time() - tick_start
            sleep   = max(0, TICK_INTERVAL - elapsed)
            time.sleep(sleep)

    # ─────────────────────────────────────────
    #  Tick update
    # ─────────────────────────────────────────
    def update(self):
        now = time.time()

        # Update all items — physics
        for item in list(self.items.values()):
            item.update()
            # Item fell off screen without being sliced
            if item.is_off_screen() and item.alive:
                item.alive = False
                if item.type not in (ITEM_BOMB, ITEM_MEGA_BOMB,
                                     ITEM_STAR_FRUIT, ITEM_MAGNET):
                    self.on_miss(item)

        # Remove dead items
        self.items = {
            k: v for k, v in self.items.items() if v.alive
        }

        # Spawn new items
        if now >= self.next_spawn_time:
            self.spawn_item()
            self.next_spawn_time = now + random.uniform(
                SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX
            )

        # Maybe spawn star fruit (server decides unpredictably)
        self.ticks_since_star += 1
        hunger_bonus = self.ticks_since_star * 0.001
        if random.random() < (STAR_BASE_CHANCE + hunger_bonus):
            self.spawn_specific(ITEM_STAR_FRUIT)
            self.ticks_since_star = 0

        # Maybe spawn mega bomb (rare)
        if random.random() < MEGA_BOMB_CHANCE:
            self.spawn_specific(ITEM_MEGA_BOMB)

        # Update shield states from current gestures
        for player in self.players:
            _, _, gesture = self.finger.get(player, (0, 0, GESTURE_NONE))
            self.shield_active[player] = (gesture == GESTURE_SHIELD)

    # ─────────────────────────────────────────
    #  Spawning
    # ─────────────────────────────────────────
    def spawn_item(self):
        """Spawn a random fruit or bomb."""
        weights = [5, 4, 3, 2, 2, 2, 1]   # watermelon→banana→bomb
        types   = [
            ITEM_WATERMELON, ITEM_APPLE, ITEM_ORANGE,
            ITEM_PINEAPPLE,  ITEM_BANANA,
            ITEM_BOMB, ITEM_BOMB
        ]
        # In versus mode add magnet fruit occasionally
        if self.mode == MODE_VERSUS and random.random() < 0.08:
            item_type = ITEM_MAGNET
        else:
            item_type = random.choices(types, weights=weights, k=1)[0]

        self.spawn_specific(item_type)

    def spawn_specific(self, item_type: str):
        """Spawn a specific item type with random arc trajectory."""
        x   = random.uniform(SCREEN_W * 0.15, SCREEN_W * 0.85)
        y   = SCREEN_H + 10
        vx  = random.uniform(-3, 3)
        # Upward velocity — enough to reach mid-screen
        vy  = random.uniform(-18, -12)

        # Banana gets a curved arc (extra horizontal velocity)
        if item_type == ITEM_BANANA:
            vx = random.choice([-5, 5])

        item = Item(item_type, x, y, vx, vy)
        self.items[item.id] = item
        return item

    # ─────────────────────────────────────────
    #  Input processing  (called ~30x/sec per player)
    # ─────────────────────────────────────────
    def process_input(self, username: str, x: float, y: float,
                      gesture: str, server_time: int) -> list:
        """
        Check if this finger position hits any item.
        Returns list of event log strings — Murex signal.
        """
        nx = x / SCREEN_W if x > 1 else x
        ny = y / SCREEN_H if y > 1 else y
        px = nx * SCREEN_W
        py = ny * SCREEN_H

        self.finger[username] = (nx, ny, gesture)
        events = []

        if gesture not in (GESTURE_SLICE, GESTURE_DOUBLE_SLICE):
            return events

        # Wider blade radius for DOUBLE_SLICE gesture
        radius = SLICE_RADIUS * (1.8 if gesture == GESTURE_DOUBLE_SLICE else 1.0)

        for item in list(self.items.values()):
            if not item.alive:
                continue

            # Distance check — hit detection
            dist = math.sqrt((item.x - px)**2 + (item.y - py)**2)
            if dist > radius:
                continue

            # HIT — process the slice
            item.alive     = False
            item.sliced_by = username
            result_events  = self.on_slice(username, item, server_time)
            events.extend(result_events)

        return events

    # ─────────────────────────────────────────
    #  Slice outcomes
    # ─────────────────────────────────────────
    def on_slice(self, username: str, item: Item, server_time: int) -> list:
        """Handle what happens when a player slices an item."""
        events = []
        ts     = server_time

        if item.type == ITEM_BOMB:
            if self.shield_active.get(username):
                # Shield blocks the bomb — no damage
                events.append(
                    f"BOMB_BLOCKED username={username} item={item.id} t={ts}"
                )
            else:
                self.apply_lives(username, -1)
                events.append(
                    f"BOMB_HIT username={username} item={item.id} lives={self.get_lives(username)} t={ts}"
                )

        elif item.type == ITEM_MEGA_BOMB:
            if self.shield_active.get(username):
                self.apply_lives(username, -1)   # shield only absorbs 1 life
                events.append(
                    f"MEGA_BOMB_PARTIAL_BLOCK username={username} item={item.id} t={ts}"
                )
            else:
                self.apply_lives(username, -2)
                events.append(
                    f"MEGA_BOMB_HIT username={username} item={item.id} lives={self.get_lives(username)} t={ts}"
                )

        elif item.type == ITEM_STAR_FRUIT:
            self.apply_lives(username, +1)
            events.append(
                f"STAR_FRUIT_HIT username={username} lives={self.get_lives(username)} t={ts}"
            )

        elif item.type == ITEM_MAGNET and self.mode == MODE_VERSUS:
            # Steal 5 points from opponent
            opponent = self.get_opponent(username)
            if opponent:
                stolen = min(5, self.scores.get(opponent, 0))
                self.scores[opponent]  = max(0, self.scores[opponent] - stolen)
                self.scores[username] += stolen
                events.append(
                    f"MAGNET_STEAL username={username} opponent={opponent} stolen={stolen} t={ts}"
                )

        else:
            # Regular fruit
            points = ITEM_POINTS.get(item.type, 0)
            self.scores[username] = self.scores.get(username, 0) + points
            events.append(
                f"SLICE_HIT username={username} item_type={item.type} "
                f"item={item.id} pts={points} score={self.scores[username]} t={ts}"
            )

            # Co-op coordination bonus — if both sliced within 0.3s
            # (simplified: just award the slicer here)

        return events

    def on_miss(self, item: Item):
        if item.type in (ITEM_BOMB, ITEM_MEGA_BOMB,
                     ITEM_STAR_FRUIT, ITEM_MAGNET):
            return   # missing these is fine

        if self.mode == MODE_COOP:
            self.apply_lives("shared", -1)
        elif self.mode == MODE_VERSUS:
            for p in self.players:
                self.apply_lives(p, -1)
        else:
            # SOLO — only one player
            if self.players:
                self.apply_lives(self.players[0], -1)

    # ─────────────────────────────────────────
    #  Lives helpers
    # ─────────────────────────────────────────
    def apply_lives(self, key: str, delta: int):
        if key in self.lives:
            self.lives[key] = max(0, self.lives[key] + delta)
        elif self.mode == MODE_COOP and "shared" in self.lives:
            self.lives["shared"] = max(0, self.lives["shared"] + delta)

    def get_lives(self, username: str) -> int:
        if self.mode == MODE_COOP:
            return self.lives.get("shared", 0)
        return self.lives.get(username, 0)

    def get_opponent(self, username: str):
        for p in self.players:
            if p != username:
                return p
        return None

    # ─────────────────────────────────────────
    #  Game over
    # ─────────────────────────────────────────
    def is_game_over(self) -> bool:
         if not self.players:
            return False
         if self.mode == MODE_COOP:
            return self.lives.get("shared", 1) <= 0
         return all(self.lives.get(p, 1) <= 0 for p in self.players)

    def finish(self):
        """Determine winner and end the room."""
        self.active = False
        winner      = self.determine_winner()

        state = self.get_state()
        state["winner"] = winner
        state["players"] = self.players
        state["leaderboard"] = self.server.leaderboard.get_top()

        msg = build_message(MSG_GAME_OVER, state)
        self.server.broadcast_room(self.room_id, msg)
        self.server.end_room(self.room_id, winner)

    def determine_winner(self):
        if self.mode == MODE_COOP:
            return "team" if any(s > 0 for s in self.scores.values()) else None
        # Versus / solo — highest score wins
        if not self.scores:
            return None
        return max(self.scores, key=self.scores.get)

    # ─────────────────────────────────────────
    #  State broadcast
    # ─────────────────────────────────────────
    def _state_lives(self) -> dict:
        if self.mode == MODE_COOP:
            return {"shared": self.lives.get("shared", LIVES_COOP)}

        default_lives = LIVES_SOLO if self.mode == MODE_SOLO else LIVES_VERSUS
        return {
            player: self.lives.get(player, default_lives)
            for player in self.players
        }

    def get_state(self) -> dict:
        """Package full game state for broadcasting — Murex signal."""
        return {
            "room_id"    : self.room_id,
            "mode"       : self.mode,
            "scores"     : self.scores,
            "lives"      : self._state_lives(),
            "items"      : [i.to_dict() for i in self.items.values()],
            "fingers"    : {
                p: {"x": fx, "y": fy, "gesture": fg}
                for p, (fx, fy, fg) in self.finger.items()
            },
            "shields"    : self.shield_active,
            "server_time": int(time.time() * 1000)
        }

    def broadcast_state(self):
        print(f"Broadcasting state to room {self.room_id}, items={len(self.items)}")
        msg = build_message(MSG_GAME_STATE, self.get_state())
        self.server.broadcast_room(self.room_id, msg)
