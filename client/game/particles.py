import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import random
import pygame
from typing import List

from shared.protocol import (
    ITEM_WATERMELON,
    ITEM_APPLE,
    ITEM_ORANGE,
    ITEM_PINEAPPLE,
    ITEM_BANANA,
    ITEM_BOMB,
    ITEM_MEGA_BOMB,
)


class Particle:
    def __init__(self, x: float, y: float, vx: float, vy: float, lifetime: int, color: tuple[int, int, int], radius: float):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.color = color
        self.radius = radius

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1
        self.radius = max(0.0, self.radius - 0.15)

    def is_dead(self) -> bool:
        return self.lifetime <= 0 or self.radius <= 0.0


class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def emit(self, x: float, y: float, color: tuple[int, int, int], count: int = 12):
        for _ in range(count):
            vx = random.uniform(-3.5, 3.5)
            vy = random.uniform(-4.5, -1.0)
            lifetime = random.randint(15, 28)
            radius = random.uniform(3.5, 6.0)
            self.particles.append(Particle(x, y, vx, vy, lifetime, color, radius))

    def update(self):
        for particle in self.particles:
            particle.update()
        self.particles = [p for p in self.particles if not p.is_dead()]

    def draw(self, surface: pygame.Surface):
        for particle in self.particles:
            if particle.radius > 0:
                pygame.draw.circle(surface, particle.color, (int(particle.x), int(particle.y)), int(particle.radius))

    def clear(self):
        self.particles.clear()


def get_fruit_color(item_type: str) -> tuple[int, int, int]:
    return {
        ITEM_WATERMELON: (220, 50, 50),
        ITEM_APPLE: (180, 30, 30),
        ITEM_ORANGE: (255, 140, 0),
        ITEM_PINEAPPLE: (255, 200, 0),
        ITEM_BANANA: (255, 220, 50),
        ITEM_BOMB: (80, 80, 80),
        ITEM_MEGA_BOMB: (255, 100, 0),
    }.get(item_type, (255, 255, 255))


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("SliceWars Particle Test")
    clock = pygame.time.Clock()
    particles = ParticleSystem()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                particles.emit(x, y, (255, 50, 50), count=24)

        particles.update()
        screen.fill((20, 20, 30))
        particles.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
