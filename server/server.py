import socket
import threading
import json
import time
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)
sys.path.append(os.path.join(ROOT, "server"))

from shared.protocol import *
from game_logic import GameRoom
from leaderboard import Leaderboard

# ─────────────────────────────────────────────
#  SliceWars Server
#  
#  Architecture (Murex signal):
#  - Single source of truth — all game state lives here
#  - Every message is timestamped on arrival
#  - Event logger records every game action with ms precision
#  - Ping/pong latency tracking per client
#  - Tick-based game loop runs independently of client connections
# ─────────────────────────────────────────────

class Client:
    """Represents one connected player."""
    def __init__(self, conn, addr):
        self.conn       = conn
        self.addr       = addr
        self.username   = None
        self.room_id    = None        # which game room they are in
        self.latency_ms = 0           # measured round-trip time
        self.connected  = True
        self.buffer     = ""          # incomplete message buffer

    def send(self, message: str):
        """Send a message to this client. Silently drops if disconnected."""
        try:
            self.conn.sendall((message + MSG_DELIMITER).encode("utf-8"))
        except Exception:
            self.connected = False

    def __repr__(self):
        return f"Client({self.username or self.addr})"


class SliceWarsServer:
    def __init__(self, host: str, port: int):
        self.host        = host
        self.port        = port
        self.clients     = {}          # username → Client
        self.rooms       = {}          # room_id  → GameRoom
        self.lock        = threading.Lock()
        self.leaderboard = Leaderboard()
        self.running     = False

        # Event logger — Murex signal
        # Every game event is written here with a ms timestamp
        self.log_file = open("server_events.log", "a", buffering=1)
        self.log(f"SERVER_START host={host} port={port}")

    # ─────────────────────────────────────────
    #  Event logger
    # ─────────────────────────────────────────
    def log(self, event: str):
        """Write a timestamped event to the log file and console."""
        ts = int(time.time() * 1000)
        line = f"[{ts}] {event}"
        self.log_file.write(line + "\n")
        print(line)

    # ─────────────────────────────────────────
    #  Start server
    # ─────────────────────────────────────────
    def start(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((self.host, self.port))
        server_sock.listen(10)
        self.running = True
        print(f"\n SliceWars server running on {self.host}:{self.port}")
        print(f" Waiting for players...\n")

        # Accept clients in main thread
        while self.running:
            try:
                conn, addr = server_sock.accept()
                # Each client gets its own thread
                client = Client(conn, addr)
                t = threading.Thread(
                    target=self.handle_client,
                    args=(client,),
                    daemon=True
                )
                t.start()
                self.log(f"CONNECTION_NEW addr={addr}")
            except Exception as e:
                print(f"Accept error: {e}")
                break

    # ─────────────────────────────────────────
    #  Client handler — runs in its own thread
    # ─────────────────────────────────────────
    def handle_client(self, client: Client):
        """
        Reads data from client socket continuously.
        Messages are newline-delimited JSON.
        """
        print(f"handle_client started for {client.addr}")
        while client.connected:
            try:
                data = client.conn.recv(BUFFER_SIZE).decode("utf-8")
                if not data:
                    break

                # Buffer incomplete messages
                client.buffer += data
                while MSG_DELIMITER in client.buffer:
                    raw, client.buffer = client.buffer.split(MSG_DELIMITER, 1)
                    raw = raw.strip()
                    if raw:
                        self.process_message(client, raw)

            except Exception as e:
                self.log(f"RECV_ERROR username={client.username} err={e}")
                break

        self.disconnect_client(client)

    # ─────────────────────────────────────────
    #  Message router
    # ─────────────────────────────────────────
    def process_message(self, client, raw):
        try:
            msg_type = None
            msg = parse_message(raw)
            if not msg:
                return
            msg = stamp(msg)
            msg_type = msg.get("type")
            payload  = msg.get("payload", {})

            if   msg_type == MSG_CONNECT:      self.on_connect(client, payload, msg["server_time"])
            elif msg_type == MSG_CHAT:         self.on_chat(client, payload)
            elif msg_type == MSG_INVITE:       self.on_invite(client, payload)
            elif msg_type == MSG_INVITE_REPLY: self.on_invite_reply(client, payload)
            elif msg_type == MSG_READY:        self.on_ready(client, payload)
            elif msg_type == MSG_MODE_SELECT:  self.on_mode_select(client, payload)
            elif msg_type == MSG_FINGER:       self.on_finger(client, payload, msg["server_time"])
            elif msg_type == MSG_PING:         self.on_ping(client, payload, msg["server_time"])
            elif msg_type == MSG_DISCONNECT:   self.disconnect_client(client)
            elif msg_type == MSG_SPECTATE:     self.on_spectate(client, payload)
            elif msg_type == "SOLO_START":     self.on_solo_start(client, payload)
            elif msg_type == "GET_USERS":      self.broadcast_user_list()
            else:
                self.log(f"UNKNOWN_MSG type={msg_type}")
        except Exception as e:
            self.log(f"PROCESS_ERROR type={msg_type} err={e}")
            import traceback
            traceback.print_exc()

    # ─────────────────────────────────────────
    #  Handlers
    # ─────────────────────────────────────────
    def on_connect(self, client: Client, payload: dict, server_time: int):
        username = payload.get("username", "").strip()

        # Validate: not empty, not too long, not already taken
        if not username or len(username) > 20:
            client.send(build_message(MSG_CONNECT_FAIL, {
                "reason": "Username must be 1–20 characters."
            }))
            return

        # Case-insensitive uniqueness check
        with self.lock:
            taken = any(
                u.lower() == username.lower()
                for u in self.clients.keys()
            )
            if taken:
                client.send(build_message(MSG_CONNECT_FAIL, {
                    "reason": f"'{username}' is already taken."
                }))
                return

            client.username = username
            self.clients[username] = client

        self.log(f"PLAYER_JOIN username={username} addr={client.addr}")

        # Confirm to the joining player
        client.send(build_message(MSG_CONNECT_OK, {
            "username"    : username,
            "server_time" : server_time
        }))

        # Send current online players list to everyone
        self.broadcast_user_list()

    def on_chat(self, client: Client, payload: dict):
        if not client.username:
            return
        text = payload.get("text", "").strip()
        room = payload.get("room", "lobby")
        if not text:
            return

        self.log(f"CHAT username={client.username} room={room} text={text[:50]}")

        msg = build_message(MSG_CHAT, {
            "username" : client.username,
            "text"     : text,
            "room"     : room
        })

        # Lobby chat → broadcast to all; room chat → broadcast to room only
        if room == "lobby":
            self.broadcast_all(msg)
        else:
            self.broadcast_room(client.room_id, msg)

    def on_invite(self, client: Client, payload: dict):
        if not client.username:
            return
        to_user = payload.get("to")
        with self.lock:
            target = self.clients.get(to_user)
        if not target:
            return

        self.log(f"INVITE from={client.username} to={to_user}")
        target.send(build_message(MSG_INVITED, {
            "from": client.username
        }))

    def on_invite_reply(self, client: Client, payload: dict):
        if not client.username:
            return
        to_user  = payload.get("to")
        accepted = payload.get("accepted", False)

        with self.lock:
            inviter = self.clients.get(to_user)
        if not inviter:
            return

        self.log(f"INVITE_REPLY from={client.username} to={to_user} accepted={accepted}")

        if accepted:
            inviter.send(build_message(MSG_INVITE_ACCEPT, {
                "from": client.username
            }))
            # Create a game room for these two players
            self.create_room(inviter, client)
        else:
            inviter.send(build_message(MSG_INVITE_DECLINE, {
                "from": client.username
            }))

    def on_mode_select(self, client: Client, payload: dict):
        mode = payload.get("mode", MODE_SOLO)
        room = self.get_room(client)
        if room:
            room.set_mode(mode)
            self.log(f"MODE_SELECT room={client.room_id} mode={mode}")

    def on_ready(self, client: Client, payload: dict):
        room = self.get_room(client)
        if not room:
            return
        room.set_ready(client.username)
        self.log(f"PLAYER_READY username={client.username} room={client.room_id}")

        # Start game when all players in room are ready
        if room.consume_start_request():
            self.start_game(room)

    def on_solo_start(self, client, payload):
        print(f"on_solo_start called username={client.username}")
        if not client.username:
            return
        room_id = client.username + "_solo"
        room = GameRoom(
            room_id = room_id,
            players = [client.username],
            server  = self
        )
        room.set_mode(MODE_SOLO)
        room.set_ready(client.username)
        with self.lock:
            self.rooms[room_id] = room
            client.room_id = room_id
        self.log(f"SOLO_START username={client.username}")
        client.send(build_message(MSG_GAME_START, {
            "room_id" : room_id,
            "players" : [client.username],
            "mode"    : MODE_SOLO
        }))
        self.start_game(room)

    def on_finger(self, client: Client, payload: dict, server_time: int):
        """
        Receive finger position + gesture from client.
        Passed directly to the game room for slice validation.
        This runs ~30 times per second per client.
        """
        room = self.get_room(client)
        if not room or not room.active:
            return

        x       = payload.get("x", 0)
        y       = payload.get("y", 0)
        gesture = payload.get("gesture", GESTURE_NONE)

        events = room.process_input(client.username, x, y, gesture, server_time)

        # Log every significant game event — Murex signal
        for event in events:
            self.log(event)

    def on_ping(self, client: Client, payload: dict, server_time: int):
        """
        Ping/pong latency system — Murex signal.
        Client sends ping with its local time.
        Server replies with pong immediately.
        Client measures round-trip time.
        """
        client_time = payload.get("client_time", 0)
        client.send(build_message(MSG_PONG, {
            "client_time" : client_time,
            "server_time" : server_time
        }))

    def on_spectate(self, client: Client, payload: dict):
        room_id = payload.get("room_id")
        with self.lock:
            room = self.rooms.get(room_id)
        if room:
            room.add_spectator(client.username)
            self.log(f"SPECTATOR_JOIN username={client.username} room={room_id}")

    # ─────────────────────────────────────────
    #  Room management
    # ─────────────────────────────────────────
    def create_room(self, player1: Client, player2: Client):
        """Create a game room for two matched players."""
        room_id = f"{player1.username}_vs_{player2.username}"
        room = GameRoom(
            room_id   = room_id,
            players   = [player1.username, player2.username],
            server    = self
        )
        with self.lock:
            self.rooms[room_id] = room
            player1.room_id = room_id
            player2.room_id = room_id

        self.log(f"ROOM_CREATED room={room_id}")

        # Notify both players they are now in a room
        room_msg = build_message(MSG_GAME_START, {
            "room_id"  : room_id,
            "players"  : [player1.username, player2.username],
            "mode"     : MODE_VERSUS,  # default, players can change
            "phase"    : "room"
        })
        player1.send(room_msg)
        player2.send(room_msg)

    def start_game(self, room):
        """Launch the game loop for a room in its own thread."""
        self.log(f"GAME_START room={room.room_id} mode={room.mode}")
        self.broadcast_room(room.room_id, build_message(MSG_GAME_START, {
            "room_id" : room.room_id,
            "players" : room.players,
            "mode"    : room.mode,
            "phase"   : "match"
        }))
        t = threading.Thread(target=room.run, daemon=True)
        t.start()

    def get_room(self, client: Client):
        """Get the GameRoom a client is currently in."""
        if not client.room_id:
            return None
        with self.lock:
            return self.rooms.get(client.room_id)

    def end_room(self, room_id: str, winner: str):
        """Clean up a finished game room."""
        with self.lock:
            room = self.rooms.pop(room_id, None)
            if not room:
                return
            for username in room.players:
                client = self.clients.get(username)
                if client:
                    client.room_id = None

        if winner:
            self.leaderboard.record_win(winner)
            self.log(f"GAME_OVER room={room_id} winner={winner}")

        self.broadcast_user_list()

    # ─────────────────────────────────────────
    #  Disconnect
    # ─────────────────────────────────────────
    def disconnect_client(self, client: Client):
        """Handle a client disconnecting cleanly."""
        client.connected = False

        if not client.username:
            return

        with self.lock:
            self.clients.pop(client.username, None)

        self.log(f"PLAYER_LEAVE username={client.username}")

        # If they were in a game, end it
        room = self.get_room(client)
        if room and room.active:
            room.active = False
            # Notify the other player
            for uname in room.players:
                if uname != client.username:
                    with self.lock:
                        other = self.clients.get(uname)
                    if other:
                        other.send(build_message(MSG_ERROR, {
                            "reason": f"{client.username} disconnected."
                        }))

        self.broadcast_user_list()

        try:
            client.conn.close()
        except Exception:
            pass

    # ─────────────────────────────────────────
    #  Broadcast helpers
    # ─────────────────────────────────────────
    def broadcast_all(self, message: str):
        """Send a message to every connected client."""
        with self.lock:
            clients = list(self.clients.values())
        for client in clients:
            client.send(message)

    def broadcast_room(self, room_id: str, message: str):
        """Send a message to every player + spectator in a room."""
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return
            usernames = room.players + list(room.spectators)
        for uname in usernames:
            with self.lock:
                client = self.clients.get(uname)
            if client:
                client.send(message)

    def broadcast_user_list(self):
        """Send the updated online players list to all clients."""
        with self.lock:
            users = [
                {   
                    "username" : u,
                    "in_game"  : self.clients[u].room_id is not None
                }
                for u in self.clients
            ]
        print(f"Broadcasting user list: {[u['username'] for u in users]} to {len(self.clients)} clients")
        self.broadcast_all(build_message(MSG_USER_LIST, {"users": users}))

    def send_to(self, username: str, message: str):
        """Send a message to a specific player by username."""
        with self.lock:
            client = self.clients.get(username)
        if client:
            client.send(message)


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    host = os.environ.get("HOST", "0.0.0.0")
    server = SliceWarsServer(host, port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.log_file.close()
