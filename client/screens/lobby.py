# client/screens/lobby.py
import pygame
import sys
import os
import time
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.protocol import (
    msg_chat, msg_invite, msg_invite_reply,
    MSG_USER_LIST, MSG_CHAT, MSG_INVITED,
    MSG_INVITE_ACCEPT, MSG_GAME_START,
    build_message
)

WIDTH             = 800
HEIGHT            = 600
BG_COLOR          = (40, 40, 40)
PANEL_PADDING     = 20
LEFT_PANEL_WIDTH  = 280
PLAYER_ROW_HEIGHT = 40
MAX_CHAT_LINES    = 12
CHAT_INPUT_HEIGHT = 44

WHITE       = (255, 255, 255)
GRAY        = (180, 180, 180)
DARKER_GRAY = (60, 60, 60)
BLUE        = (50, 115, 220)
HOVER_BLUE  = (70, 135, 240)
POPUP_BG    = (30, 30, 30)
GREEN_BG    = (40, 100, 40)


def draw_text(surface, text, font, color, center):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=center)
    surface.blit(rendered, rect)


def wrap_text(font, text, max_width):
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class Button:
    def __init__(self, rect, text, font):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font

    def draw(self, surface, mouse_pos):
        color = HOVER_BLUE if self.rect.collidepoint(mouse_pos) else BLUE
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        draw_text(surface, self.text, self.font, WHITE, self.rect.center)

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos))


class InputBox:
    def __init__(self, rect, font, max_length=200):
        self.rect       = pygame.Rect(rect)
        self.font       = font
        self.text       = ""
        self.active     = False
        self.max_length = max_length

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return "submit"
            elif event.unicode and len(self.text) < self.max_length:
                self.text += event.unicode
        return None

    def draw(self, surface):
        color = WHITE if self.active else GRAY
        pygame.draw.rect(surface, DARKER_GRAY, self.rect, border_radius=6)
        display = self.text if self.text else "Type a message..."
        rendered = self.font.render(display, True, color)
        surface.blit(rendered, (
            self.rect.x + 8,
            self.rect.y + (self.rect.height - rendered.get_height()) // 2
        ))


class LobbyScreen:
    def __init__(self, screen, net, username):
        self.screen        = screen
        self.net           = net
        self.username      = username
        self.user_list     = []
        self.chat_messages = []
        self.invite_from   = None
        self.invite_popup  = False
        self.return_payload = None

        self.chat_input = InputBox(
            (LEFT_PANEL_WIDTH + 2 * PANEL_PADDING,
             HEIGHT - CHAT_INPUT_HEIGHT - PANEL_PADDING,
             WIDTH - LEFT_PANEL_WIDTH - 3 * PANEL_PADDING - 100,
             CHAT_INPUT_HEIGHT),
            pygame.font.SysFont(None, 24),
        )
        self.send_button = Button(
            (WIDTH - PANEL_PADDING - 90,
             HEIGHT - CHAT_INPUT_HEIGHT - PANEL_PADDING,
             90, CHAT_INPUT_HEIGHT),
            "Send", pygame.font.SysFont(None, 24),
        )
        self.solo_button = Button(
            (PANEL_PADDING, PANEL_PADDING + 44, LEFT_PANEL_WIDTH, 36),
            "Play Solo", pygame.font.SysFont(None, 24),
        )
        self.popup_accept = Button(
            (WIDTH // 2 - 110, HEIGHT // 2 + 40, 100, 36),
            "Accept", pygame.font.SysFont(None, 24),
        )
        self.popup_decline = Button(
            (WIDTH // 2 + 10, HEIGHT // 2 + 40, 100, 36),
            "Decline", pygame.font.SysFont(None, 24),
        )

        # Register callbacks BEFORE requesting user list
        self.net.on(MSG_USER_LIST,     self._on_user_list)
        self.net.on(MSG_CHAT,          self._on_chat)
        self.net.on(MSG_INVITED,       self._on_invited)
        self.net.on(MSG_INVITE_ACCEPT, self._on_invite_accept)
        self.net.on(MSG_GAME_START,    self._on_game_start)

        # Request user list immediately and again after short delay
        self.net.send(build_message("GET_USERS", {}))
        def delayed_refresh():
            time.sleep(0.3)
            self.net.send(build_message("GET_USERS", {}))
        threading.Thread(target=delayed_refresh, daemon=True).start()

    # ─────────────────────────────────────────
    #  Callbacks
    # ─────────────────────────────────────────
    def _on_user_list(self, payload, server_time):
        users = payload.get("users", []) if isinstance(payload, dict) else []
        if isinstance(users, list):
            self.user_list = list(users)

    def _on_chat(self, payload, server_time):
        if not isinstance(payload, dict):
            return
        if payload.get("room") != "lobby":
            return
        uname = payload.get("username", "")
        text  = payload.get("text", "")
        self.chat_messages.append(f"{uname}: {text}")
        self.chat_messages = self.chat_messages[-MAX_CHAT_LINES:]

    def _on_invited(self, payload, server_time):
        if isinstance(payload, dict):
            inviter = payload.get("from")
            if inviter:
                self.invite_from  = inviter
                self.invite_popup = True

    def _on_invite_accept(self, payload, server_time):
        if isinstance(payload, dict) and payload.get("room_id"):
            self.return_payload = payload

    def _on_game_start(self, payload, server_time):
        if isinstance(payload, dict):
            self.return_payload = payload

    # ─────────────────────────────────────────
    #  Send helpers
    # ─────────────────────────────────────────
    def _send_invite(self, target):
        if target and target != self.username:
            self.net.send(msg_invite(self.username, target))

    def _send_chat(self, text):
        text = text.strip()
        if not text:
            return
        self.net.send(msg_chat(self.username, text, "lobby"))
        self.chat_input.text = ""

    def _reply_invite(self, accepted):
        if not self.invite_from:
            return
        self.net.send(msg_invite_reply(self.username, self.invite_from, accepted))
        self.invite_popup = False
        self.invite_from  = None

    # ─────────────────────────────────────────
    #  Drawing
    # ─────────────────────────────────────────
    def _draw_player_list(self, mouse_pos):
        panel_rect = pygame.Rect(
            PANEL_PADDING, PANEL_PADDING + 100,
            LEFT_PANEL_WIDTH, HEIGHT - 2 * PANEL_PADDING - 100
        )
        pygame.draw.rect(self.screen, DARKER_GRAY, panel_rect, border_radius=8)
        tfont = pygame.font.SysFont(None, 24)
        draw_text(self.screen, "Online Players", tfont, WHITE,
                  (panel_rect.centerx, panel_rect.y + 18))

        y        = panel_rect.y + 48
        row_font = pygame.font.SysFont(None, 22)
        for user in self.user_list:
            if y + PLAYER_ROW_HEIGHT > panel_rect.bottom:
                break
            uname   = user.get("username", "")
            in_game = user.get("in_game", False)
            is_me   = uname.lower() == self.username.lower()
            row_rect = pygame.Rect(
                panel_rect.x + 8, y,
                panel_rect.width - 16, PLAYER_ROW_HEIGHT - 6
            )
            if is_me:
                bg = GREEN_BG
            elif row_rect.collidepoint(mouse_pos):
                bg = HOVER_BLUE
            else:
                bg = (80, 80, 80)
            pygame.draw.rect(self.screen, bg, row_rect, border_radius=6)
            if is_me:
                label = f"{uname} (you)"
            elif in_game:
                label = f"{uname} (in game)"
            else:
                label = uname
            draw_text(self.screen, label, row_font, WHITE, row_rect.center)
            y += PLAYER_ROW_HEIGHT

    def _draw_chat_panel(self, mouse_pos):
        panel_x    = LEFT_PANEL_WIDTH + 2 * PANEL_PADDING
        panel_rect = pygame.Rect(
            panel_x, PANEL_PADDING + 80,
            WIDTH - panel_x - PANEL_PADDING,
            HEIGHT - 3 * PANEL_PADDING - CHAT_INPUT_HEIGHT - 80
        )
        pygame.draw.rect(self.screen, DARKER_GRAY, panel_rect, border_radius=8)
        tfont = pygame.font.SysFont(None, 24)
        draw_text(self.screen, "Lobby Chat", tfont, WHITE,
                  (panel_rect.centerx, panel_rect.y + 18))
        chat_y    = panel_rect.y + 48
        line_font = pygame.font.SysFont(None, 20)
        avail_w   = panel_rect.width - 16
        for message in self.chat_messages[-MAX_CHAT_LINES:]:
            for line in wrap_text(line_font, message, avail_w):
                rendered = line_font.render(line, True, WHITE)
                self.screen.blit(rendered, (panel_rect.x + 10, chat_y))
                chat_y += rendered.get_height() + 4
                if chat_y > panel_rect.bottom - 20:
                    break
        self.chat_input.draw(self.screen)
        self.send_button.draw(self.screen, mouse_pos)

    def _draw_popup(self, mouse_pos):
        popup_rect = pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2 - 90, 440, 180)
        pygame.draw.rect(self.screen, POPUP_BG, popup_rect, border_radius=12)
        pygame.draw.rect(self.screen, BLUE, popup_rect, 2, border_radius=12)
        font = pygame.font.SysFont(None, 24)
        draw_text(self.screen,
                  f"{self.invite_from} invited you to play!",
                  font, WHITE,
                  (popup_rect.centerx, popup_rect.y + 45))
        self.popup_accept.draw(self.screen, mouse_pos)
        self.popup_decline.draw(self.screen, mouse_pos)

    # ─────────────────────────────────────────
    #  Main loop
    # ─────────────────────────────────────────
    def run(self):
        clock      = pygame.time.Clock()
        title_font = pygame.font.SysFont(None, 28)
        running    = True
        frame      = 0

        while running:
            frame += 1
            # Re-request user list every 60 frames (~1 sec) to stay fresh
            if frame % 60 == 0:
                self.net.send(build_message("GET_USERS", {}))

            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                result = self.chat_input.handle_event(event)
                if result == "submit":
                    self._send_chat(self.chat_input.text)

                if self.send_button.is_clicked(event):
                    self._send_chat(self.chat_input.text)

                if self.invite_popup:
                    if self.popup_accept.is_clicked(event):
                        self._reply_invite(True)
                    elif self.popup_decline.is_clicked(event):
                        self._reply_invite(False)
                else:
                    if self.solo_button.is_clicked(event):
                        self.return_payload = {
                            "room_id": self.username + "_solo",
                            "players": [self.username],
                            "mode"   : "SOLO",
                        }
                    if (event.type == pygame.MOUSEBUTTONDOWN
                            and event.button == 1):
                        panel_rect = pygame.Rect(
                            PANEL_PADDING, PANEL_PADDING + 100,
                            LEFT_PANEL_WIDTH,
                            HEIGHT - 2 * PANEL_PADDING - 100
                        )
                        y = panel_rect.y + 48
                        for user in self.user_list:
                            row_rect = pygame.Rect(
                                panel_rect.x + 8, y,
                                panel_rect.width - 16,
                                PLAYER_ROW_HEIGHT - 6
                            )
                            if row_rect.collidepoint(event.pos):
                                target = user.get("username")
                                if target and target != self.username:
                                    self._send_invite(target)
                                break
                            y += PLAYER_ROW_HEIGHT

            self.screen.fill(BG_COLOR)
            draw_text(self.screen,
                      f"Logged in as {self.username}",
                      title_font, WHITE,
                      (WIDTH // 2, PANEL_PADDING + 25))
            self.solo_button.draw(self.screen, mouse_pos)
            self._draw_player_list(mouse_pos)
            self._draw_chat_panel(mouse_pos)
            if self.invite_popup:
                self._draw_popup(mouse_pos)
            pygame.display.flip()
            clock.tick(60)

            if self.return_payload is not None:
                running = False

        return self.return_payload


def run(screen, net, username):
    if screen is None:
        pygame.init()
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("SliceWars Lobby")
    lobby = LobbyScreen(screen, net, username)
    return lobby.run()


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("SliceWars Lobby Test")

    class MockNet:
        def __init__(self):
            self.on_message = {}
        def on(self, msg_type, callback):
            self.on_message[msg_type] = callback
        def send(self, msg):
            print("Sent:", msg[:80])
        def simulate(self, msg_type, payload):
            if msg_type in self.on_message:
                self.on_message[msg_type](payload, 0)

    net = MockNet()
    lobby = LobbyScreen(screen, net, "Jad")
    net.simulate(MSG_USER_LIST, {"users": [
        {"username": "Jad", "in_game": False},
        {"username": "Dad", "in_game": False},
    ]})
    result = lobby.run()
    print("Lobby returned:", result)