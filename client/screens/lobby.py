# client/screens/lobby.py
# Pygame screen for the main lobby after a player connects.
# Shows online players, lobby chat, and handles invitations using protocol messages.

import pygame
import time
from typing import Optional

try:
    from shared.protocol import (
        msg_chat,
        msg_invite,
        msg_invite_reply,
        MSG_USER_LIST,
        MSG_CHAT,
        MSG_INVITED,
        MSG_INVITE_ACCEPT,
    )
except Exception:
    # Fallback definitions if shared.protocol is not available at import time.
    def msg_chat(username, text, room="lobby"):
        return {"type": "CHAT", "payload": {"username": username, "text": text, "room": room}}

    def msg_invite(from_user, to_user):
        return {"type": "INVITE", "payload": {"from": from_user, "to": to_user}}

    def msg_invite_reply(from_user, to_user, accepted):
        return {"type": "INVITE_REPLY", "payload": {"from": from_user, "to": to_user, "accepted": accepted}}

    MSG_USER_LIST = "USER_LIST"
    MSG_CHAT = "CHAT"
    MSG_INVITED = "INVITED"
    MSG_INVITE_ACCEPT = "INVITE_ACCEPT"

WIDTH = 800
HEIGHT = 600
BG_COLOR = (40, 40, 40)
PANEL_PADDING = 20
LEFT_PANEL_WIDTH = 280
CHAT_PANEL_PADDING = 12
PLAYER_ROW_HEIGHT = 40
MAX_CHAT_LINES = 12
CHAT_INPUT_HEIGHT = 44

WHITE = (255, 255, 255)
GRAY = (180, 180, 180)
DARKER_GRAY = (60, 60, 60)
BLUE = (50, 115, 220)
HOVER_BLUE = (70, 135, 240)
POPUP_BG = (30, 30, 30)
RED = (220, 60, 60)


def draw_text(surface, text, font, color, center):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=center)
    surface.blit(rendered, rect)


def wrap_text(font, text, max_width):
    words = text.split(" ")
    lines = []
    current = ""
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
        hovered = self.rect.collidepoint(mouse_pos)
        color = HOVER_BLUE if hovered else BLUE
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        draw_text(surface, self.text, self.font, WHITE, self.rect.center)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


class InputBox:
    def __init__(self, rect, font, max_length=200):
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
                return "submit"
            elif event.unicode and len(self.text) < self.max_length:
                self.text += event.unicode
        return None

    def draw(self, surface):
        color = WHITE if self.active else GRAY
        pygame.draw.rect(surface, DARKER_GRAY, self.rect, border_radius=6)
        display_text = self.text if self.text else "Type a message..."
        rendered = self.font.render(display_text, True, color)
        surface.blit(rendered, (self.rect.x + 8, self.rect.y + (self.rect.height - rendered.get_height()) // 2))


class LobbyScreen:
    def __init__(self, screen, net, username):
        self.screen = screen
        self.net = net
        self.username = username
        self.chat_input = InputBox(
            (
                LEFT_PANEL_WIDTH + 2 * PANEL_PADDING,
                HEIGHT - CHAT_INPUT_HEIGHT - PANEL_PADDING,
                WIDTH - LEFT_PANEL_WIDTH - 3 * PANEL_PADDING - 100,
                CHAT_INPUT_HEIGHT,
            ),
            pygame.font.SysFont(None, 24),
        )
        self.send_button = Button(
            (
                WIDTH - PANEL_PADDING - 90,
                HEIGHT - CHAT_INPUT_HEIGHT - PANEL_PADDING,
                90,
                CHAT_INPUT_HEIGHT,
            ),
            "Send",
            pygame.font.SysFont(None, 24),
        )
        self.user_list = []
        self.chat_messages = []
        self.invite_from = None
        self.invite_popup = False
        self.popup_accept = Button((WIDTH // 2 - 110, HEIGHT // 2 + 40, 100, 36), "Accept", pygame.font.SysFont(None, 24))
        self.popup_decline = Button((WIDTH // 2 + 10, HEIGHT // 2 + 40, 100, 36), "Decline", pygame.font.SysFont(None, 24))
        self.return_payload = None
        self._saved_callbacks = {}
        self._register_callbacks()

    def _register_callbacks(self):
        for msg_type, handler in [
            (MSG_USER_LIST, self._on_user_list),
            (MSG_CHAT, self._on_chat),
            (MSG_INVITED, self._on_invited),
            (MSG_INVITE_ACCEPT, self._on_invite_accept),
        ]:
            self._saved_callbacks[msg_type] = getattr(self.net, "on_message", {}).get(msg_type)
            if hasattr(self.net, "on"):
                self.net.on(msg_type, handler)
            else:
                setattr(self.net, f"_lobby_handler_{msg_type}", handler)

    def _restore_callbacks(self):
        if hasattr(self.net, "on_message"):
            for msg_type, callback in self._saved_callbacks.items():
                if callback is None:
                    self.net.on_message.pop(msg_type, None)
                else:
                    self.net.on_message[msg_type] = callback

    def _on_user_list(self, payload, server_time):
        users = payload.get("users", []) if isinstance(payload, dict) else []
        if isinstance(users, list):
            self.user_list = users

    def _on_chat(self, payload, server_time):
        if not isinstance(payload, dict):
            return
        room = payload.get("room")
        if room != "lobby":
            return
        username = payload.get("username", "")
        text = payload.get("text", "")
        self.chat_messages.append(f"{username}: {text}")
        self.chat_messages = self.chat_messages[-MAX_CHAT_LINES:]

    def _on_invited(self, payload, server_time):
        if not isinstance(payload, dict):
            return
        inviter = payload.get("from")
        if inviter:
            self.invite_from = inviter
            self.invite_popup = True

    def _on_invite_accept(self, payload, server_time):
        self.return_payload = payload

    def _send_invite(self, target_username):
        if target_username and target_username != self.username:
            if hasattr(self.net, "send"):
                self.net.send(msg_invite(self.username, target_username))
            elif hasattr(self.net, "invite"):
                self.net.invite(self.username, target_username)

    def _send_chat(self, text):
        text = text.strip()
        if not text:
            return
        if hasattr(self.net, "send"):
            self.net.send(msg_chat(self.username, text, "lobby"))
        elif hasattr(self.net, "chat"):
            self.net.chat(self.username, text, "lobby")
        self.chat_messages.append(f"{self.username}: {text}")
        self.chat_messages = self.chat_messages[-MAX_CHAT_LINES:]
        self.chat_input.text = ""

    def _reply_invite(self, accepted):
        if not self.invite_from:
            return
        if hasattr(self.net, "send"):
            self.net.send(msg_invite_reply(self.username, self.invite_from, accepted))
        elif hasattr(self.net, "reply_invite"):
            self.net.reply_invite(self.username, self.invite_from, accepted)
        self.invite_popup = False
        self.invite_from = None

    def _draw_player_list(self, mouse_pos):
        panel_rect = pygame.Rect(PANEL_PADDING, PANEL_PADDING + 80, LEFT_PANEL_WIDTH, HEIGHT - 2 * PANEL_PADDING - 80)
        pygame.draw.rect(self.screen, DARKER_GRAY, panel_rect, border_radius=8)
        title_font = pygame.font.SysFont(None, 24)
        draw_text(self.screen, "Online Players", title_font, WHITE, (panel_rect.centerx, panel_rect.y + 18))
        y = panel_rect.y + 48
        row_font = pygame.font.SysFont(None, 22)
        for user in self.user_list:
            if y + PLAYER_ROW_HEIGHT > panel_rect.bottom:
                break
            username = user.get("username", "")
            in_game = user.get("in_game", False)
            row_rect = pygame.Rect(panel_rect.x + 8, y, panel_rect.width - 16, PLAYER_ROW_HEIGHT - 6)
            hovered = row_rect.collidepoint(mouse_pos)
            bg_color = HOVER_BLUE if hovered else (80, 80, 80)
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=6)
            label = f"{username} {'(in game)' if in_game else ''}".strip()
            draw_text(self.screen, label, row_font, WHITE, row_rect.center)
            y += PLAYER_ROW_HEIGHT
        return panel_rect

    def _draw_chat_panel(self, mouse_pos):
        panel_x = LEFT_PANEL_WIDTH + 2 * PANEL_PADDING
        panel_rect = pygame.Rect(panel_x, PANEL_PADDING + 80, WIDTH - panel_x - PANEL_PADDING, HEIGHT - 3 * PANEL_PADDING - CHAT_INPUT_HEIGHT - 80)
        pygame.draw.rect(self.screen, DARKER_GRAY, panel_rect, border_radius=8)
        title_font = pygame.font.SysFont(None, 24)
        draw_text(self.screen, "Lobby Chat", title_font, WHITE, (panel_rect.centerx, panel_rect.y + 18))
        chat_y = panel_rect.y + 48
        line_font = pygame.font.SysFont(None, 20)
        available_width = panel_rect.width - 16
        for message in self.chat_messages[-MAX_CHAT_LINES:]:
            lines = wrap_text(line_font, message, available_width)
            for line in lines:
                rendered = line_font.render(line, True, WHITE)
                self.screen.blit(rendered, (panel_rect.x + 10, chat_y))
                chat_y += rendered.get_height() + 4
                if chat_y > panel_rect.bottom - 20:
                    break
            if chat_y > panel_rect.bottom - 20:
                break
        self.chat_input.draw(self.screen)
        self.send_button.draw(self.screen, mouse_pos)
        return panel_rect

    def _draw_popup(self, mouse_pos):
        popup_rect = pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2 - 90, 440, 180)
        pygame.draw.rect(self.screen, POPUP_BG, popup_rect, border_radius=12)
        pygame.draw.rect(self.screen, BLUE, popup_rect, 2, border_radius=12)
        message = f"{self.invite_from} invited you to play"
        title_font = pygame.font.SysFont(None, 24)
        draw_text(self.screen, message, title_font, WHITE, (popup_rect.centerx, popup_rect.y + 45))
        self.popup_accept.draw(self.screen, mouse_pos)
        self.popup_decline.draw(self.screen, mouse_pos)

    def run(self):
        clock = pygame.time.Clock()
        title_font = pygame.font.SysFont(None, 28)
        running = True
        while running:
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
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        panel_rect = pygame.Rect(PANEL_PADDING, PANEL_PADDING + 80, LEFT_PANEL_WIDTH, HEIGHT - 2 * PANEL_PADDING - 80)
                        y = panel_rect.y + 48
                        for user in self.user_list:
                            row_rect = pygame.Rect(panel_rect.x + 8, y, panel_rect.width - 16, PLAYER_ROW_HEIGHT - 6)
                            if row_rect.collidepoint(event.pos):
                                target_username = user.get("username")
                                if target_username and target_username != self.username:
                                    self._send_invite(target_username)
                                break
                            y += PLAYER_ROW_HEIGHT
            self.screen.fill(BG_COLOR)
            draw_text(self.screen, f"Logged in as {self.username}", title_font, WHITE, (WIDTH // 2, PANEL_PADDING + 25))
            self._draw_player_list(mouse_pos)
            self._draw_chat_panel(mouse_pos)
            if self.invite_popup:
                self._draw_popup(mouse_pos)
            pygame.display.flip()
            clock.tick(60)
            if self.return_payload is not None:
                running = False
        self._restore_callbacks()
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

        def send(self, message):
            print("Sent:", message)

        def simulate(self, msg_type, payload):
            if msg_type in self.on_message:
                self.on_message[msg_type](payload, int(time.time() * 1000))

    net = MockNet()
    lobby_screen = LobbyScreen(screen, net, "TestUser")
    net.simulate(MSG_USER_LIST, {"users": [{"username": "TestUser", "in_game": False}, {"username": "Other", "in_game": True}, {"username": "Alice", "in_game": False}]})
    net.simulate(MSG_CHAT, {"username": "Alice", "text": "Hello lobby!", "room": "lobby"})
    net.simulate(MSG_INVITED, {"from": "Other"})
    result = lobby_screen.run()
    print("Lobby returned:", result)
