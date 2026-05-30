# client/screens/pre_lobby.py
# Pygame screen where the player types a username before connecting.
# The screen sends a connect message via the provided NetworkClient using
# `msg_connect(username)` from `shared.protocol` and reacts to
# `MSG_CONNECT_OK` and `MSG_CONNECT_FAIL` responses.

import pygame
import time
from typing import Optional

try:
    from shared.protocol import msg_connect, MSG_CONNECT_OK, MSG_CONNECT_FAIL
except Exception:
    # If protocol definitions are missing at import time, still allow the
    # module to be imported. The real project must provide these symbols.
    def msg_connect(username):
        return ("MSG_CONNECT", username)

    MSG_CONNECT_OK = "MSG_CONNECT_OK"
    MSG_CONNECT_FAIL = "MSG_CONNECT_FAIL"

WIDTH = 800
HEIGHT = 600
BG_COLOR = (40, 40, 40)
TITLE_FONT_SIZE = 56
INPUT_FONT_SIZE = 32
BUTTON_FONT_SIZE = 28

WHITE = (255, 255, 255)
RED = (220, 60, 60)
GREEN = (100, 220, 120)
GRAY = (180, 180, 180)
BLUE = (50, 115, 220)


def draw_text(surface, text, font, color, center):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=center)
    surface.blit(surf, rect)


class InputBox:
    def __init__(self, rect, font, max_length=20):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.text = ""
        self.active = False
        self.max_length = max_length

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                # let caller handle submission via Connect button
                pass
            else:
                char = event.unicode
                if char and len(self.text) < self.max_length:
                    self.text += char

    def draw(self, surface):
        color = WHITE if self.active else GRAY
        pygame.draw.rect(surface, (60, 60, 60), self.rect, border_radius=6)
        txt_surf = self.font.render(self.text or "Enter username...", True, color)
        txt_rect = txt_surf.get_rect(midleft=(self.rect.x + 10, self.rect.centery))
        surface.blit(txt_surf, txt_rect)


class Button:
    def __init__(self, rect, text, font):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font

    def draw(self, surface, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        color = BLUE if not hovered else (70, 135, 240)
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        draw_text(surface, self.text, self.font, WHITE, self.rect.center)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


def _poll_messages(network_client):
    """
    Try several common ways to obtain incoming messages from the provided
    NetworkClient. Returns a list of messages (possibly empty). This helper
    is permissive to match different client implementations used in the
    project; the message shape is checked by the caller.
    """
    if network_client is None:
        return []

    # Common method names to try
    for method in ("get_messages", "poll", "recv", "receive", "get"):
        if hasattr(network_client, method):
            try:
                fn = getattr(network_client, method)
                res = fn()
                if res is None:
                    return []
                return res if isinstance(res, (list, tuple)) else [res]
            except Exception:
                continue

    # Fallback: check for an 'incoming' attribute that's a list
    if hasattr(network_client, "incoming"):
        try:
            inc = getattr(network_client, "incoming")
            return list(inc)
        except Exception:
            return []

    return []


def _message_type(msg):
    if msg is None:
        return None
    if isinstance(msg, dict) and "type" in msg:
        return msg["type"]
    if isinstance(msg, (list, tuple)) and len(msg) > 0:
        return msg[0]
    return msg


def _message_reason(msg):
    if msg is None:
        return ""
    if isinstance(msg, dict):
        return msg.get("reason") or msg.get("error") or ""
    if isinstance(msg, (list, tuple)) and len(msg) > 1:
        return msg[1]
    return ""


def run(network_client, screen: Optional[pygame.Surface] = None):
    """
    Run the pre-lobby username input screen.

    Parameters:
    - network_client: a connected NetworkClient instance (required)
    - screen: optional existing pygame Surface to render into

    Returns: the chosen username (string) when MSG_CONNECT_OK is received.
    """
    if network_client is None:
        raise ValueError("network_client is required")

    pygame.init()
    if screen is None:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("SliceWars - Connect")

    title_font = pygame.font.SysFont(None, TITLE_FONT_SIZE)
    input_font = pygame.font.SysFont(None, INPUT_FONT_SIZE)
    button_font = pygame.font.SysFont(None, BUTTON_FONT_SIZE)
    clock = pygame.time.Clock()

    input_box = InputBox((WIDTH // 2 - 200, 240, 400, 50), input_font, max_length=20)
    connect_button = Button((WIDTH // 2 - 80, 320, 160, 48), "Connect", button_font)

    error_text = ""
    error_color = RED
    error_time = 0
    accepted = False

    saved_ok = getattr(network_client, "on_message", {}).get(MSG_CONNECT_OK)
    saved_fail = getattr(network_client, "on_message", {}).get(MSG_CONNECT_FAIL)

    def on_connect_ok(payload, server_time):
        nonlocal accepted
        accepted = True

    def on_connect_fail(payload, server_time):
        nonlocal error_text, error_time
        reason = ""
        if isinstance(payload, dict):
            reason = payload.get("reason", "")
        error_text = reason or "Connection failed"
        error_time = time.time()

    if hasattr(network_client, "on"):
        network_client.on(MSG_CONNECT_OK, on_connect_ok)
        network_client.on(MSG_CONNECT_FAIL, on_connect_fail)

    running = True
    username = ""

    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            input_box.handle_event(event)
            if connect_button.is_clicked(event):
                username = input_box.text.strip()
                if not username:
                    error_text = "Username cannot be empty"
                    error_time = time.time()
                elif len(username) > 20:
                    error_text = "Username must be <= 20 characters"
                    error_time = time.time()
                else:
                    # send connect message using protocol helper
                    try:
                        msg = msg_connect(username)
                        # attempt common send method names
                        sent = False
                        for send_name in ("send", "send_msg", "send_message", "write"):
                            if hasattr(network_client, send_name):
                                try:
                                    getattr(network_client, send_name)(msg)
                                    sent = True
                                    break
                                except Exception:
                                    continue
                        if not sent and hasattr(network_client, "socket"):
                            try:
                                # best-effort raw socket send if available
                                network_client.socket.sendall(repr(msg).encode())
                                sent = True
                            except Exception:
                                pass
                        if not sent:
                            error_text = "Failed to send connect message"
                            error_time = time.time()
                    except Exception as e:
                        error_text = f"Connect error: {e}"
                        error_time = time.time()

        if accepted:
            if hasattr(network_client, "on_message"):
                if saved_ok is None:
                    network_client.on_message.pop(MSG_CONNECT_OK, None)
                else:
                    network_client.on_message[MSG_CONNECT_OK] = saved_ok
                if saved_fail is None:
                    network_client.on_message.pop(MSG_CONNECT_FAIL, None)
                else:
                    network_client.on_message[MSG_CONNECT_FAIL] = saved_fail
            return username

        # Poll for incoming network messages, for mock clients used in tests.
        msgs = _poll_messages(network_client)
        for m in msgs:
            mtype = _message_type(m)
            if mtype == MSG_CONNECT_OK:
                # connection accepted; return the username to caller
                return username
            if mtype == MSG_CONNECT_FAIL:
                reason = _message_reason(m) or "Connection failed"
                error_text = str(reason)
                error_time = time.time()

        screen.fill(BG_COLOR)
        draw_text(screen, "SliceWars", title_font, WHITE, (WIDTH // 2, 120))

        input_box.draw(screen)
        connect_button.draw(screen, mouse_pos)

        # show validation/error message
        if error_text:
            draw_text(screen, error_text, input_font, error_color, (WIDTH // 2, 420))

        pygame.display.flip()
        clock.tick(60)

    return None


if __name__ == "__main__":
    # Minimal local test harness: a mock NetworkClient that accepts any
    # username and replies with MSG_CONNECT_OK after a short delay.
    class MockNetworkClient:
        def __init__(self):
            self._sent = None
            self._reply_sent = False

        def send(self, msg):
            self._sent = msg

        def get_messages(self):
            # Once a send is observed, reply with OK (simulate server)
            if self._sent and not self._reply_sent:
                self._reply_sent = True
                return [(MSG_CONNECT_OK, )]
            return []

    mc = MockNetworkClient()
    res = run(mc)
    print("Returned username:", res)
