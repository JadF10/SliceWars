import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pygame
import math
from shared.protocol import (
    ITEM_BOMB,
    ITEM_MEGA_BOMB,
    ITEM_STAR_FRUIT,
    ITEM_MAGNET,
)


def draw_bomb(surface: pygame.Surface, x: int, y: int, radius: int):
    pygame.draw.circle(surface, (0, 0, 0), (x, y), radius)
    fuse_top_y = y - radius - 8
    pygame.draw.line(surface, (150, 100, 50), (x, y - radius), (x, fuse_top_y), 2)


def draw_mega_bomb(surface: pygame.Surface, x: int, y: int, radius: int, pulse: float = 0):
    scale = 1.0 + pulse * 0.1
    r = int(radius * scale * 3)
    base_color = (220, 60, 0)

    points = []
    for i in range(12):
        angle = (i / 12) * 2 * math.pi
        d = r if i % 2 == 0 else r * 0.7
        px = x + d * math.cos(angle)
        py = y + d * math.sin(angle)
        points.append((px, py))

    pygame.draw.polygon(surface, base_color, points)

    fuse_top_y = y - r - 12
    pygame.draw.line(surface, (150, 100, 50), (x, y - r), (x, fuse_top_y), 3)


def draw_star_fruit(surface: pygame.Surface, x: int, y: int, radius: int, glow: float = 0):
    glow_r = int(radius * (1.2 + glow * 0.3))
    glow_color = (255, 215, 0, int(100 * (1 - glow)))
    glow_surface = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow_surface, (*glow_color[:3], glow_color[3] if len(glow_color) > 3 else 100), (glow_r, glow_r), glow_r)
    surface.blit(glow_surface, (x - glow_r, y - glow_r), special_flags=pygame.BLEND_ALPHA_SDL2)

    points = []
    for i in range(10):
        angle = (i / 10) * 2 * math.pi - math.pi / 2
        d = radius if i % 2 == 0 else radius * 0.4
        px = x + d * math.cos(angle)
        py = y + d * math.sin(angle)
        points.append((px, py))

    pygame.draw.polygon(surface, (255, 215, 0), points)


def draw_magnet_fruit(surface: pygame.Surface, x: int, y: int, radius: int):
    pygame.draw.circle(surface, (255, 180, 0), (x, y), radius)
    font = pygame.font.SysFont("Arial", int(radius * 1.5), bold=True)
    text = font.render("M", True, (60, 40, 0))
    text_rect = text.get_rect(center=(x, y))
    surface.blit(text, text_rect)


def draw_item(surface: pygame.Surface, item_dict: dict):
    item_type = item_dict.get("type")
    x = int(item_dict.get("x", 0))
    y = int(item_dict.get("y", 0))
    radius = int(item_dict.get("radius", 20))

    if item_type == ITEM_BOMB:
        draw_bomb(surface, x, y, radius)
    elif item_type == ITEM_MEGA_BOMB:
        pulse = item_dict.get("pulse", 0)
        draw_mega_bomb(surface, x, y, radius, pulse)
    elif item_type == ITEM_STAR_FRUIT:
        glow = item_dict.get("glow", 0)
        draw_star_fruit(surface, x, y, radius, glow)
    elif item_type == ITEM_MAGNET:
        draw_magnet_fruit(surface, x, y, radius)


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((900, 600))
    pygame.display.set_caption("SliceWars Items Test")
    clock = pygame.time.Clock()
    frame = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        frame += 1
        pulse = (math.sin(frame * 0.05) + 1) / 2
        glow = (math.sin(frame * 0.07) + 1) / 2

        screen.fill((16, 22, 42))

        draw_bomb(screen, 100, 150, 16)

        mega_dict = {"type": ITEM_MEGA_BOMB, "x": 280, "y": 150, "radius": 20, "pulse": pulse}
        draw_item(screen, mega_dict)

        star_dict = {"type": ITEM_STAR_FRUIT, "x": 450, "y": 150, "radius": 24, "glow": glow}
        draw_item(screen, star_dict)

        magnet_dict = {"type": ITEM_MAGNET, "x": 620, "y": 150, "radius": 20}
        draw_item(screen, magnet_dict)

        font = pygame.font.SysFont("Arial", 16)
        labels = ["Bomb", "Mega Bomb", "Star Fruit", "Magnet"]
        x_positions = [100, 280, 450, 620]
        for label, x_pos in zip(labels, x_positions):
            text = font.render(label, True, (255, 255, 255))
            screen.blit(text, (x_pos - text.get_width() // 2, 200))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
