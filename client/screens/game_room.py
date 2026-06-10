# client/screens/game_room.py
import pygame
import sys
import os
import time
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.protocol import (
    msg_chat, MSG_GAME_START, MSG_CHAT,
    MODE_COOP, MODE_VERSUS, build_message,
    MSG_MODE_SELECT, MSG_READY
)

WIDTH  = 800
HEIGHT = 600
BG_COLOR     = (40, 40, 40)
PANEL_COLOR  = (60, 60, 60)
BUTTON_COLOR = (50, 115, 220)
BUTTON_HOVER = (70, 135, 240)
BUTTON_ACTIVE= (60, 180, 90)
BUTTON_GRAY  = (80, 80, 80)
BUTTON_GRAY_H= (100, 100, 100)
TEXT_COLOR   = (255, 255, 255)
INPUT_BG     = (30, 30, 30)
MUTED        = (150, 150, 150)
GREEN_TEXT   = (150, 220, 150)


def draw_text(surface, text, font, color, center):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=center)
    surface.blit(rendered, rect)


class Button:
    def __init__(self, rect, text, font, gray=False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.gray = gray

    def draw(self, surface, mouse_pos, active=False):
        hovered = self.rect.collidepoint(mouse_pos)
        if self.gray:
            color = BUTTON_GRAY_H if hovered else BUTTON_GRAY
        elif active:
            color = BUTTON_ACTIVE
        else:
            color = BUTTON_HOVER if hovered else BUTTON_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        draw_text(surface, self.text, self.font, TEXT_COLOR, self.rect.center)

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
        pygame.draw.rect(surface, INPUT_BG, self.rect, border_radius=8)
        color   = TEXT_COLOR if self.text else MUTED
        display = self.text if self.text else "Type a chat message..."
        rendered = self.font.render(display, True, color)
        surface.blit(rendered, (
            self.rect.x + 8,
            self.rect.y + (self.rect.height - rendered.get_height()) // 2
        ))


class GameRoomScreen:
    def __init__(self, screen, net, username, room_id, players,
                 current_input="mouse"):
        self.screen        = screen
        self.net           = net
        self.username      = username
        self.room_id       = room_id
        self.players       = players[:2] if len(players) >= 2 else players
        self.mode          = MODE_VERSUS
        self.ready         = False
        self.chat_messages = []
        self.return_mode   = None
        self.current_input = current_input

        font24 = pygame.font.SysFont(None, 24)
        font26 = pygame.font.SysFont(None, 26)
        font22 = pygame.font.SysFont(None, 22)

        # Mode buttons — Co-op and Versus only (no Solo)
        self.mode_buttons = [
            Button((WIDTH // 2 - 155, 220, 140, 50), "Co-op",  font24),
            Button((WIDTH // 2 + 15,  220, 140, 50), "Versus", font24),
        ]
        self.mode_values = [MODE_COOP, MODE_VERSUS]

        # Ready button
        self.ready_button = Button(
            (WIDTH // 2 - 90, 300, 180, 52), "Ready", font26
        )

        # Input toggle button — top right corner
        switch_label = "Switch to Webcam" if current_input == "mouse" else "Switch to Mouse"
        self.input_toggle = Button(
            (WIDTH - 210, 16, 195, 34), switch_label, font22, gray=True
        )

        # Chat
        self.chat_input = InputBox(
            (20, HEIGHT - 70, WIDTH - 140, 44), font22
        )
        self.send_button = Button(
            (WIDTH - 110, HEIGHT - 70, 90, 44), "Send", font22
        )

        self._register_callbacks()

    def _register_callbacks(self):
        self.net.on(MSG_CHAT,       self._on_chat)
        self.net.on(MSG_GAME_START, self._on_game_start)

    def _on_chat(self, payload, server_time):
        if not isinstance(payload, dict):
            return
        if payload.get("room") != "room":
            return
        uname = payload.get("username", "")
        text  = payload.get("text", "")
        self.chat_messages.append(f"{uname}: {text}")
        self.chat_messages = self.chat_messages[-6:]

    def _on_game_start(self, payload, server_time):
        if isinstance(payload, dict):
            self.return_mode = self.mode

    def _send_mode_select(self, mode):
        self.mode = mode
        self.net.send(build_message(MSG_MODE_SELECT, {"mode": mode}))

    def _send_ready(self):
        if not self.ready:
            self.ready = True
            self.net.send(build_message(MSG_READY, {}))

    def _send_chat(self):
        text = self.chat_input.text.strip()
        if not text:
            return
        self.net.send(msg_chat(self.username, text, room="room"))
        self.chat_input.text = ""

    def run(self):
        clock      = pygame.time.Clock()
        title_font = pygame.font.SysFont(None, 32)
        label_font = pygame.font.SysFont(None, 24)
        chat_font  = pygame.font.SysFont(None, 20)
        small_font = pygame.font.SysFont(None, 21)
        running    = True

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

                # Input toggle
                if self.input_toggle.is_clicked(event):
                    if self.current_input == "mouse":
                        self.current_input = "webcam"
                        self.input_toggle.text = "Switch to Mouse"
                    else:
                        self.current_input = "mouse"
                        self.input_toggle.text = "Switch to Webcam"

                # Mode buttons
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, button in enumerate(self.mode_buttons):
                        if button.is_clicked(event):
                            self._send_mode_select(self.mode_values[i])
                            break

            # ── Draw ──────────────────────────
            self.screen.fill(BG_COLOR)

            # Title
            players_str = (f"{self.players[0]} vs {self.players[1]}"
                           if len(self.players) >= 2 else self.players[0])
            draw_text(self.screen, f"Game Room: {players_str}",
                      title_font, TEXT_COLOR, (WIDTH // 2, 80))

            # Input status — top right, above the toggle button
            currently = "Webcam" if self.current_input == "webcam" else "Mouse"
            status_text = small_font.render(
                f"Currently using: {currently}", True, MUTED)
            self.screen.blit(status_text, (WIDTH - 210, 56))

            # Input toggle button
            self.input_toggle.draw(self.screen, mouse_pos)

            # Mode label
            draw_text(self.screen, "Select Game Mode",
                      label_font, MUTED, (WIDTH // 2, 185))

            # Mode buttons
            for i, button in enumerate(self.mode_buttons):
                active = self.mode == self.mode_values[i]
                button.draw(self.screen, mouse_pos, active=active)

            # Current mode indicator
            mode_label = "Co-op" if self.mode == MODE_COOP else "Versus"
            draw_text(self.screen, f"Mode: {mode_label}",
                      small_font, GREEN_TEXT, (WIDTH // 2, 285))

            # Ready button
            self.ready_button.draw(self.screen, mouse_pos, active=self.ready)
            if self.ready:
                waiting = small_font.render(
                    "Waiting for opponent...", True, TEXT_COLOR)
                self.screen.blit(waiting, waiting.get_rect(
                    center=self.ready_button.rect.center))

            # Chat panel
            chat_rect = pygame.Rect(20, HEIGHT - 240, WIDTH - 40, 150)
            pygame.draw.rect(self.screen, PANEL_COLOR, chat_rect, border_radius=8)
            pygame.draw.rect(self.screen, (120, 120, 120), chat_rect, 2, border_radius=8)
            draw_text(self.screen, "Room Chat", label_font, TEXT_COLOR,
                      (chat_rect.centerx, chat_rect.y + 16))
            chat_y = chat_rect.y + 40
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

        return self.return_mode, self.current_input


def run(screen, net, username, room_id, players, current_input="mouse"):
    if screen is None:
        pygame.init()
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("SliceWars Game Room")
    room = GameRoomScreen(screen, net, username, room_id, players, current_input)
    return room.run()


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("SliceWars Game Room Test")

    class MockNet:
        def __init__(self):
            self.on_message = {}
        def on(self, msg_type, callback):
            if msg_type not in self.on_message:
                self.on_message[msg_type] = []
            self.on_message[msg_type].append(callback)
        def send(self, msg):
            print("SEND:", str(msg)[:80])

    net = MockNet()
    result = run(screen, net, "Player1", "room42", ["Player1", "Player2"], "mouse")
    print("Game room returned:", result)