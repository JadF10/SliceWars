# client/screens/game_room.py
# Pygame waiting room screen after two players are matched, before the game starts.

import pygame
import threading
import time
from typing import Optional

try:
    from shared.protocol import (
        msg_chat,
        msg_ready,
        msg_mode_select,
        MSG_GAME_START,
        MODE_SOLO,
        MODE_COOP,
        MODE_VERSUS,
        MSG_CHAT,
    )
except Exception:
    def msg_chat(username, text, room="room"):
        return {"type": "CHAT", "payload": {"username": username, "text": text, "room": room}}

    def msg_ready():
        return {"type": "READY", "payload": {}}

    def msg_mode_select(mode):
        return {"type": "MODE_SELECT", "payload": {"mode": mode}}

    MSG_GAME_START = "GAME_START"
    MODE_SOLO = "SOLO"
    MODE_COOP = "COOP"
    MODE_VERSUS = "VERSUS"
    MSG_CHAT = "CHAT"

WIDTH = 800
HEIGHT = 600
BG_COLOR = (40, 40, 40)
PANEL_COLOR = (60, 60, 60)
BUTTON_COLOR = (50, 115, 220)
BUTTON_HOVER = (70, 135, 240)
BUTTON_ACTIVE = (60, 180, 90)
TEXT_COLOR = (255, 255, 255)
INPUT_BG = (30, 30, 30)


def draw_text(surface, text, font, color, center):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=center)
    surface.blit(rendered, rect)


class Button:
    def __init__(self, rect, text, font):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font

    def draw(self, surface, mouse_pos, active=False):
        hovered = self.rect.collidepoint(mouse_pos)
        if active:
            color = BUTTON_ACTIVE
        else:
            color = BUTTON_HOVER if hovered else BUTTON_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        draw_text(surface, self.text, self.font, TEXT_COLOR, self.rect.center)

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
        pygame.draw.rect(surface, INPUT_BG, self.rect, border_radius=8)
        color = TEXT_COLOR if self.text else (180, 180, 180)
        display = self.text if self.text else "Type a chat message..."
        rendered = self.font.render(display, True, color)
        surface.blit(rendered, (self.rect.x + 8, self.rect.y + (self.rect.height - rendered.get_height()) // 2))


class GameRoomScreen:
    def __init__(self, screen, net, username, room_id, players):
        self.screen = screen
        self.net = net
        self.username = username
        self.room_id = room_id
        self.players = players[:2]
        self.mode = MODE_VERSUS
        self.ready = False
        self.chat_input = InputBox((20, HEIGHT - 70, WIDTH - 140, 44), pygame.font.SysFont(None, 22))
        self.send_button = Button((WIDTH - 110, HEIGHT - 70, 90, 44), "Send", pygame.font.SysFont(None, 22))
        self.mode_buttons = [
            Button((WIDTH // 2 - 220, 220, 140, 50), "Solo", pygame.font.SysFont(None, 24)),
            Button((WIDTH // 2 - 70, 220, 140, 50), "Co-op", pygame.font.SysFont(None, 24)),
            Button((WIDTH // 2 + 80, 220, 140, 50), "Versus", pygame.font.SysFont(None, 24)),
        ]
        self.ready_button = Button((WIDTH // 2 - 90, 300, 180, 52), "Ready", pygame.font.SysFont(None, 26))
        self.chat_messages = []
        self.return_mode = None
        self._saved_callbacks = {}
        self._register_callbacks()

    def _register_callbacks(self):
        for msg_type, handler in [(MSG_CHAT, self._on_chat), (MSG_GAME_START, self._on_game_start)]:
            self._saved_callbacks[msg_type] = getattr(self.net, "on_message", {}).get(msg_type)
            if hasattr(self.net, "on"):
                self.net.on(msg_type, handler)
            else:
                setattr(self.net, f"_game_room_handler_{msg_type}", handler)

    def _restore_callbacks(self):
        if hasattr(self.net, "on_message"):
            for msg_type, callback in self._saved_callbacks.items():
                if callback is None:
                    self.net.on_message.pop(msg_type, None)
                else:
                    self.net.on_message[msg_type] = callback

    def _on_chat(self, payload, server_time):
        if not isinstance(payload, dict):
            return
        if payload.get("room") != "room":
            return
        username = payload.get("username", "")
        text = payload.get("text", "")
        self.chat_messages.append(f"{username}: {text}")
        self.chat_messages = self.chat_messages[-6:]

    def _on_game_start(self, payload, server_time):
        self.return_mode = self.mode

    def _send_mode_select(self, mode):
        self.mode = mode
        if hasattr(self.net, "send"):
            self.net.send(msg_mode_select(mode))
        elif hasattr(self.net, "select_mode"):
            self.net.select_mode(mode)

    def _send_ready(self):
        if not self.ready:
            self.ready = True
            if hasattr(self.net, "send"):
                self.net.send(msg_ready())
            elif hasattr(self.net, "send_ready"):
                self.net.send_ready()

    def _send_chat(self):
        text = self.chat_input.text.strip()
        if not text:
            return
        if hasattr(self.net, "send"):
            self.net.send(msg_chat(self.username, text, room="room"))
        elif hasattr(self.net, "chat"):
            self.net.chat(self.username, text, room="room")
        self.chat_messages.append(f"{self.username}: {text}")
        self.chat_messages = self.chat_messages[-6:]
        self.chat_input.text = ""

    def run(self):
        clock = pygame.time.Clock()
        title_font = pygame.font.SysFont(None, 32)
        label_font = pygame.font.SysFont(None, 24)
        running = True

        while running:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                action = self.chat_input.handle_event(event)
                if action == "submit":
                    self._send_chat()
                if self.send_button.is_clicked(event):
                    self._send_chat()
                if self.ready_button.is_clicked(event):
                    self._send_ready()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, button in enumerate(self.mode_buttons):
                        if button.is_clicked(event):
                            selected = [MODE_SOLO, MODE_COOP, MODE_VERSUS][i]
                            self._send_mode_select(selected)
                            break
            self.screen.fill(BG_COLOR)
            draw_text(self.screen, f"Players: {self.players[0]} vs {self.players[1]}", title_font, TEXT_COLOR, (WIDTH // 2, 80))
            for i, button in enumerate(self.mode_buttons):
                active = self.mode == [MODE_SOLO, MODE_COOP, MODE_VERSUS][i]
                button.draw(self.screen, mouse_pos, active=active)
            ready_label = "Waiting for opponent..." if self.ready else "Ready"
            self.ready_button.draw(self.screen, mouse_pos, active=self.ready)
            if self.ready:
                ready_text = pygame.font.SysFont(None, 22).render(ready_label, True, TEXT_COLOR)
                rect = ready_text.get_rect(center=self.ready_button.rect.center)
                self.screen.blit(ready_text, rect)
            chat_rect = pygame.Rect(20, HEIGHT - 240, WIDTH - 40, 150)
            pygame.draw.rect(self.screen, PANEL_COLOR, chat_rect, border_radius=8)
            pygame.draw.rect(self.screen, (120, 120, 120), chat_rect, 2, border_radius=8)
            draw_text(self.screen, "Room Chat", label_font, TEXT_COLOR, (chat_rect.centerx, chat_rect.y + 16))
            chat_y = chat_rect.y + 40
            chat_font = pygame.font.SysFont(None, 20)
            for message in self.chat_messages:
                rendered = chat_font.render(message, True, TEXT_COLOR)
                self.screen.blit(rendered, (chat_rect.x + 10, chat_y))
                chat_y += rendered.get_height() + 6
            self.chat_input.draw(self.screen)
            self.send_button.draw(self.screen, mouse_pos)

            pygame.display.flip()
            clock.tick(60)

            if self.return_mode is not None:
                running = False

        self._restore_callbacks()
        return self.return_mode


def run(screen, net, username, room_id, players):
    if screen is None:
        pygame.init()
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("SliceWars Game Room")
    room = GameRoomScreen(screen, net, username, room_id, players)
    return room.run()


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("SliceWars Game Room Test")

    class MockNet:
        def __init__(self):
            self.on_message = {}

        def on(self, msg_type, callback):
            self.on_message[msg_type] = callback

        def send(self, message):
            print("SEND:", message)

        def simulate_game_start(self):
            callback = self.on_message.get(MSG_GAME_START)
            if callback:
                callback({}, int(time.time() * 1000))

    net = MockNet()
    room = GameRoomScreen(screen, net, "Player1", "room42", ["Player1", "Player2"])

    def delayed_start():
        time.sleep(5)
        net.simulate_game_start()

    threading.Thread(target=delayed_start, daemon=True).start()
    result = room.run()
    print("Game room returned:", result)
