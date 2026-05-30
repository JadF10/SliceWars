import socket
import threading
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.protocol import *

class NetworkClient:
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        self.host       = host
        self.port       = port
        self.sock       = None
        self.connected  = False
        self.buffer     = ""
        self.latency_ms = 0
        self._ping_time = 0
        self.on_message = {}

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            threading.Thread(target=self._receive_loop, daemon=True).start()
            threading.Thread(target=self._ping_loop, daemon=True).start()
            print(f"Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self):
        if self.connected:
            self.send(build_message(MSG_DISCONNECT, {}))
        self.connected = False
        try:
            self.sock.close()
        except Exception:
            pass

    def send(self, message):
        if not self.connected:
            return
        try:
            self.sock.sendall((message + MSG_DELIMITER).encode("utf-8"))
        except Exception:
            self.connected = False

    def _receive_loop(self):
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
            except Exception:
                break
        self.connected = False

    def _dispatch(self, raw):
        msg = parse_message(raw)
        if not msg:
            return
        msg_type = msg.get("type")
        if msg_type == MSG_PONG:
            self._handle_pong(msg["payload"])
            return
        callback = self.on_message.get(msg_type)
        if callback:
            try:
                callback(msg["payload"], msg.get("server_time", 0))
            except Exception as e:
                print(f"Callback error {msg_type}: {e}")

    def _ping_loop(self):
        while self.connected:
            self._ping_time = int(time.time() * 1000)
            self.send(msg_ping(self._ping_time))
            time.sleep(2.0)

    def _handle_pong(self, payload):
        now = int(time.time() * 1000)
        self.latency_ms = now - payload.get("client_time", now)

    def on(self, msg_type, callback):
        self.on_message[msg_type] = callback

    def join(self, username):
        self.send(msg_connect(username))

    def chat(self, username, text, room="lobby"):
        self.send(msg_chat(username, text, room))

    def invite(self, from_user, to_user):
        self.send(msg_invite(from_user, to_user))

    def reply_invite(self, from_user, to_user, accepted):
        self.send(msg_invite_reply(from_user, to_user, accepted))

    def send_finger(self, x, y, gesture):
        self.send(msg_finger(x, y, gesture))

    def send_ready(self):
        self.send(build_message(MSG_READY, {}))

    def select_mode(self, mode):
        self.send(msg_mode_select(mode))

    def spectate(self, room_id):
        self.send(build_message(MSG_SPECTATE, {"room_id": room_id}))
