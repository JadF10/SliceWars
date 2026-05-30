import socket
import threading
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.protocol import *

# ─────────────────────────────────────────────
#  SliceWars Network Client
#
#  Handles all communication with the server.
#  Runs a background receive thread so the game
#  loop never blocks waiting for data.
#
#  Murex signal:
#  - Ping/pong latency measurement
#  - Every received message has a server_time
#  - Callbacks for each message type keep
#    the architecture clean and decoupled
# ─────────────────────────────────────────────

class NetworkClient:
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host        = host
        self.port        = port
        self.sock        = None
        self.connected   = False
        self.buffer      = ""
        self.latency_ms  = 0          # measured round-trip time
        self._ping_time  = 0          # local time when ping was sent

        # Callback registry — set these from the game screens
        # e.g. client.on_message[MSG_GAME_STATE] = my_function
        self.on_message  = {}

        self._recv_thread = None
        self._ping_thread = None

    # ─────────────────────────────────────────
    #  Connect / disconnect
    # ─────────────────────────────────────────
    def connect(self) -> bool:
        """Connect to the server. Returns True on success."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True

            # Start background receive thread
            self._recv_thread = threading.Thread(
                target=self._receive_loop,
                daemon=True
            )
            self._recv_thread.start()

            # Start ping thread for latency measurement
            self._ping_thread = threading.Thread(
                target=self._ping_loop,
                daemon=True
            )
            self._ping_thread.start()

            print(f"Connected to {self.host}:{self.port}")
            return True

        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Cleanly disconnect from the server."""
        if self.connected:
            self.send(build_message(MSG_DISCONNECT, {}))
        self.connected = False
        try:
            self.sock.close()
        except Exception:
            pass

    # ─────────────────────────────────────────
    #  Send
    # ─────────────────────────────────────────
    def send(self, message: str):
        """Send a message to the server."""
        if not self.connected:
            return
        try:
            self.sock.sendall((message + MSG_DELIMITER).encode("utf-8"))
        except Exception as e:
            print(f"Send error: {e}")
            self.connected = False

    # ─────────────────────────────────────────
    #  Receive loop  (background thread)
    # ─────────────────────────────────────────
    def _receive_loop(self):
        """
        Continuously reads from socket.
        Splits on MSG_DELIMITER and dispatches each message.
        Runs in a daemon thread — dies when main program exits.
        """
        while self.connected:
            try:
                data = self.sock.recv(BUFFER_SIZE).decode("utf-8")
                if not data:
                    break

                self.buffer += data
                while MSG_DELIMITER in self.buffer:
                    raw, self.buffer = self.buffer.split(MSG_DELIMITER, 1)
                    raw = raw.strip()
                    if raw:
                        self._dispatch(raw)

            except Exception as e:
                if self.connected:
                    print(f"Receive error: {e}")
                break

        self.connected = False
        print("Disconnected from server.")

    def _dispatch(self, raw: str):
        """Parse a message and call the registered callback."""
        msg = parse_message(raw)
        if not msg:
            return

        msg_type = msg.get("type")

        # Handle pong internally — update latency
        if msg_type == MSG_PONG:
            self._handle_pong(msg["payload"])
            return

        # Call registered callback if one exists
        callback = self.on_message.get(msg_type)
        if callback:
            try:
                callback(msg["payload"], msg.get("server_time", 0))
            except Exception as e:
                print(f"Callback error for {msg_type}: {e}")

    # ─────────────────────────────────────────
    #  Latency measurement — Murex signal
    # ─────────────────────────────────────────
    def _ping_loop(self):
        """
        Sends a ping every 2 seconds.
        Server replies with pong immediately.
        We measure round-trip time.
        """
        while self.connected:
            self._ping_time = int(time.time() * 1000)
            self.send(msg_ping(self._ping_time))
            time.sleep(2.0)

    def _handle_pong(self, payload: dict):
        """Calculate latency from pong reply."""
        now         = int(time.time() * 1000)
        sent_time   = payload.get("client_time", now)
        self.latency_ms = now - sent_time

    # ─────────────────────────────────────────
    #  Convenience send methods
    # ─────────────────────────────────────────
    def join(self, username: str):
        self.send(msg_connect(username))

    def chat(self, username: str, text: str, room: str = "lobby"):
        self.send(msg_chat(username, text, room))

    def invite(self, from_user: str, to_user: str):
        self.send(msg_invite(from_user, to_user))

    def reply_invite(self, from_user: str, to_user: str, accepted: bool):
        self.send(msg_invite_reply(from_user, to_user, accepted))

    def send_finger(self, x: float, y: float, gesture: str):
        """Send finger position + gesture to server. Called ~30x/sec."""
        self.send(msg_finger(x, y, gesture))

    def send_ready(self):
        self.send(build_message(MSG_READY, {}))

    def select_mode(self, mode: str):
        self.send(msg_mode_select(mode))

    def spectate(self, room_id: str):
        self.send(build_message(MSG_SPECTATE, {"room_id": room_id}))

    # ─────────────────────────────────────────
    #  Register callbacks
    # ─────────────────────────────────────────
    def on(self, msg_type: str, callback):
        """
        Register a callback for a message type.
        Usage:
            net.on(MSG_GAME_STATE, self.handle_game_state)
        Callback signature: callback(payload: dict, server_time: int)
        """
        self.on_message[msg_type] = callback


# ─────────────────────────────────────────────
#  Quick connection test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("NetworkClient self-test — needs server running on localhost:5555")
    client = NetworkClient()

    # Register a callback for connect OK
    def on_connect_ok(payload, server_time):
        print(f"  Connected as: {payload['username']}")
        print(f"  Server time:  {server_time} ms")

    def on_user_list(payload, server_time):
        users = payload.get("users", [])
        print(f"  Online users: {[u['username'] for u in users]}")

    client.on(MSG_CONNECT_OK,   on_connect_ok)
    client.on(MSG_USER_LIST,    on_user_list)
    client.on(MSG_CONNECT_FAIL, lambda p, t: print(f"  FAILED: {p['reason']}"))

    if client.connect():
        client.join("TestPlayer")
        time.sleep(2)
        print(f"  Latency: {client.latency_ms} ms")
        client.disconnect()
    else:
        print("  Could not connect — is the server running?")
