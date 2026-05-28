import json
import time


# ─────────────────────────────────────────────
#  Message types  (client → server)
# ─────────────────────────────────────────────
MSG_CONNECT        = "CONNECT"         # client sends username
MSG_DISCONNECT     = "DISCONNECT"      # client is leaving
MSG_CHAT           = "CHAT"            # lobby or room chat message
MSG_INVITE         = "INVITE"          # invite another player
MSG_INVITE_REPLY   = "INVITE_REPLY"    # accept or decline invite
MSG_READY          = "READY"           # player is ready to start
MSG_MODE_SELECT    = "MODE_SELECT"     # solo / coop / versus
MSG_FINGER         = "FINGER"          # finger position + gesture (30/sec)
MSG_PING           = "PING"            # latency check sent by client
MSG_SPECTATE       = "SPECTATE"        # request to spectate a room

# ─────────────────────────────────────────────
#  Message types  (server → client)
# ─────────────────────────────────────────────
MSG_CONNECT_OK     = "CONNECT_OK"      # username accepted
MSG_CONNECT_FAIL   = "CONNECT_FAIL"    # username taken or invalid
MSG_USER_LIST      = "USER_LIST"       # updated list of online players
MSG_INVITED        = "INVITED"         # someone invited you
MSG_INVITE_ACCEPT  = "INVITE_ACCEPT"   # your invite was accepted
MSG_INVITE_DECLINE = "INVITE_DECLINE"  # your invite was declined
MSG_GAME_START     = "GAME_START"      # match is starting
MSG_GAME_STATE     = "GAME_STATE"      # full game state broadcast (every tick)
MSG_GAME_OVER      = "GAME_OVER"       # match ended, winner decided
MSG_PONG           = "PONG"            # latency reply from server
MSG_ERROR          = "ERROR"           # generic error message

# ─────────────────────────────────────────────
#  Gesture types  (produced by gesture classifier)
# ─────────────────────────────────────────────
GESTURE_SLICE        = "SLICE"         # index finger pointing  → blade
GESTURE_SHIELD       = "SHIELD"        # open palm              → block next bomb
GESTURE_POWER_UP     = "POWER_UP"      # closed fist            → activate multiplier
GESTURE_DOUBLE_SLICE = "DOUBLE_SLICE"  # peace sign             → wider blade
GESTURE_NONE         = "NONE"          # no hand detected

# ─────────────────────────────────────────────
#  Game modes
# ─────────────────────────────────────────────
MODE_SOLO    = "SOLO"
MODE_COOP    = "COOP"
MODE_VERSUS  = "VERSUS"

# ─────────────────────────────────────────────
#  Item types
# ─────────────────────────────────────────────
ITEM_WATERMELON  = "WATERMELON"
ITEM_APPLE       = "APPLE"
ITEM_ORANGE      = "ORANGE"
ITEM_PINEAPPLE   = "PINEAPPLE"
ITEM_BANANA      = "BANANA"
ITEM_BOMB        = "BOMB"
ITEM_MEGA_BOMB   = "MEGA_BOMB"
ITEM_STAR_FRUIT  = "STAR_FRUIT"
ITEM_MAGNET      = "MAGNET"

# Points per fruit
ITEM_POINTS = {
    ITEM_WATERMELON : 5,
    ITEM_APPLE      : 2,
    ITEM_ORANGE     : 3,
    ITEM_PINEAPPLE  : 4,
    ITEM_BANANA     : 2,
    ITEM_BOMB       : 0,
    ITEM_MEGA_BOMB  : 0,
    ITEM_STAR_FRUIT : 0,   # gives +1 life instead
    ITEM_MAGNET     : 0,   # steals 5 pts from opponent
}


# ─────────────────────────────────────────────
#  Message builder
#  Every message is a JSON object with:
#    type        → message type constant above
#    server_time → unix timestamp in ms (added by server on receipt)
#    payload     → dict of message-specific data
# ─────────────────────────────────────────────
def build_message(msg_type: str, payload: dict = None) -> str:
    """
    Build a JSON string to send over the socket.
    server_time is 0 here — the server overwrites it on receipt.
    """
    message = {
        "type"        : msg_type,
        "server_time" : 0,
        "payload"     : payload or {}
    }
    return json.dumps(message)


def parse_message(raw: str) -> dict:
    """
    Parse a raw JSON string back into a dict.
    Returns None if the message is malformed.
    """
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def stamp(message: dict) -> dict:
    """
    Server calls this on every received message to add a timestamp.
    Timestamp is in milliseconds — important for latency calculations.
    """
    message["server_time"] = int(time.time() * 1000)
    return message


# ─────────────────────────────────────────────
#  Payload helpers  — shortcuts for common messages
# ─────────────────────────────────────────────
def msg_connect(username: str) -> str:
    return build_message(MSG_CONNECT, {"username": username})

def msg_chat(username: str, text: str, room: str = "lobby") -> str:
    return build_message(MSG_CHAT, {"username": username, "text": text, "room": room})

def msg_invite(from_user: str, to_user: str) -> str:
    return build_message(MSG_INVITE, {"from": from_user, "to": to_user})

def msg_invite_reply(from_user: str, to_user: str, accepted: bool) -> str:
    return build_message(MSG_INVITE_REPLY, {
        "from": from_user, "to": to_user, "accepted": accepted
    })

def msg_finger(x: float, y: float, gesture: str) -> str:
    return build_message(MSG_FINGER, {"x": x, "y": y, "gesture": gesture})

def msg_ping(client_time: int) -> str:
    return build_message(MSG_PING, {"client_time": client_time})

def msg_mode_select(mode: str) -> str:
    return build_message(MSG_MODE_SELECT, {"mode": mode})


# ─────────────────────────────────────────────
#  Network constants
# ─────────────────────────────────────────────
DEFAULT_HOST    = "127.0.0.1"   # change to server IP for internet play
DEFAULT_PORT    = 5555
BUFFER_SIZE     = 4096          # bytes per socket read
MSG_DELIMITER   = "\n"          # messages separated by newline


if __name__ == "__main__":
    # Quick self-test — run this file directly to verify it works
    print("Testing protocol...")

    # Build and parse a CONNECT message
    raw = msg_connect("Jad")
    parsed = parse_message(raw)
    assert parsed["type"] == MSG_CONNECT
    assert parsed["payload"]["username"] == "Jad"
    print(f"  CONNECT message OK: {raw}")

    # Build and parse a FINGER message
    raw = msg_finger(0.5, 0.3, GESTURE_SLICE)
    parsed = parse_message(raw)
    assert parsed["payload"]["gesture"] == GESTURE_SLICE
    print(f"  FINGER message OK:  {raw}")

    # Test stamping
    stamped = stamp(parsed)
    assert stamped["server_time"] > 0
    print(f"  Timestamp OK:       {stamped['server_time']} ms")

    print("\nAll protocol tests passed.")