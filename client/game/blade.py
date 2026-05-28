# client/game/blade.py
# Blade trail rendering for SliceWars using pygame surfaces and transparency.

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pygame
from typing import List, Tuple

from shared.protocol import GESTURE_SLICE, GESTURE_SHIELD, GESTURE_POWER_UP, GESTURE_DOUBLE_SLICE, GESTURE_NONE

TRAIL_COLOR = (200, 220, 255)
MAX_POINTS = 12


class BladeTrail:
    def __init__(self):
        self.points: List[Tuple[int, int]] = []
        self.surface = pygame.Surface((800, 600), pygame.SRCALPHA)

    def update(self, x: int, y: int):
        point = (int(x), int(y))
        self.points.append(point)
        if len(self.points) > MAX_POINTS:
            self.points.pop(0)

    def clear(self):
        self.points.clear()

    def draw(self, surface: pygame.Surface):
        self.surface.fill((0, 0, 0, 0))
        total = len(self.points)
        for index, point in enumerate(self.points):
            if total == 0:
                continue
            fraction = (index + 1) / total
            radius = int(1 + 5 * fraction)
            alpha = int(50 + 205 * fraction)
            color = TRAIL_COLOR + (alpha,)
            pygame.draw.circle(self.surface, color, point, max(1, radius))
        surface.blit(self.surface, (0, 0))


def draw_cursor(surface: pygame.Surface, x: int, y: int, gesture: str):
    if gesture == GESTURE_SLICE:
        color = (0, 255, 0)
    elif gesture == GESTURE_SHIELD:
        color = (255, 165, 0)
    elif gesture == GESTURE_POWER_UP:
        color = (255, 50, 50)
    elif gesture == GESTURE_DOUBLE_SLICE:
        color = (0, 220, 255)
    else:
        color = (150, 150, 150)
    pygame.draw.circle(surface, color, (int(x), int(y)), 10)
    pygame.draw.circle(surface, (255, 255, 255), (int(x), int(y)), 4)


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("SliceWars Blade Trail Test")
    clock = pygame.time.Clock()

    trail = BladeTrail()
    gesture = GESTURE_NONE
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                trail.update(event.pos[0], event.pos[1])
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    gesture = GESTURE_SLICE
                elif event.key == pygame.K_2:
                    gesture = GESTURE_SHIELD
                elif event.key == pygame.K_3:
                    gesture = GESTURE_POWER_UP
                elif event.key == pygame.K_4:
                    gesture = GESTURE_DOUBLE_SLICE
                elif event.key == pygame.K_0:
                    gesture = GESTURE_NONE
            elif event.type == pygame.MOUSEBUTTONDOWN:
                trail.clear()

        screen.fill((0, 0, 0))
        trail.draw(screen)
        mouse_x, mouse_y = pygame.mouse.get_pos()
        draw_cursor(screen, mouse_x, mouse_y, gesture)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
