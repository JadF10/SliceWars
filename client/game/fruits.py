# client/game/fruits.py
# Procedural fruit drawing using pygame.draw only.

import pygame
import math

# Colors
WATERMELON_OUTER = (34, 139, 34)
WATERMELON_INNER = (255, 69, 0)
WATERMELON_SEED = (0, 0, 0)
APPLE_RED = (220, 20, 60)
APPLE_STEM = (139, 69, 19)
ORANGE_COLOR = (255, 140, 0)
ORANGE_SEGMENT = (255, 165, 0)
PINEAPPLE_COLOR = (218, 165, 32)
PINEAPPLE_LEAF = (34, 139, 34)
BANANA_COLOR = (255, 215, 0)
BANANA_SHADOW = (204, 170, 0)


def draw_watermelon(surface, x, y, radius):
    """Draw a whole watermelon: green outer, red/orange inner, black seeds."""
    # Outer green circle
    pygame.draw.circle(surface, WATERMELON_OUTER, (int(x), int(y)), int(radius))
    
    # Inner red/orange circle (slightly smaller)
    inner_radius = int(radius * 0.8)
    pygame.draw.circle(surface, WATERMELON_INNER, (int(x), int(y)), inner_radius)
    
    # Add black seeds
    seed_radius = int(radius * 0.08)
    seed_positions = [
        (int(x - radius * 0.3), int(y - radius * 0.2)),
        (int(x + radius * 0.3), int(y - radius * 0.2)),
        (int(x - radius * 0.2), int(y + radius * 0.3)),
        (int(x + radius * 0.2), int(y + radius * 0.3)),
        (int(x), int(y)),
    ]
    for sx, sy in seed_positions:
        pygame.draw.circle(surface, WATERMELON_SEED, (sx, sy), max(1, seed_radius))


def draw_watermelon_half(surface, x, y, radius, side):
    """Draw half a watermelon (left or right side)."""
    inner_radius = int(radius * 0.8)
    
    if side == "left":
        # Draw left semicircle using a polygon
        points = [(int(x), int(y - radius))]
        for i in range(90):
            angle = math.pi / 2 + (i * math.pi / 90)
            px = int(x + radius * math.cos(angle))
            py = int(y + radius * math.sin(angle))
            points.append((px, py))
        points.append((int(x), int(y)))
        if len(points) > 2:
            pygame.draw.polygon(surface, WATERMELON_OUTER, points)
        
        # Inner
        inner_points = [(int(x), int(y - inner_radius))]
        for i in range(90):
            angle = math.pi / 2 + (i * math.pi / 90)
            px = int(x + inner_radius * math.cos(angle))
            py = int(y + inner_radius * math.sin(angle))
            inner_points.append((px, py))
        inner_points.append((int(x), int(y)))
        if len(inner_points) > 2:
            pygame.draw.polygon(surface, WATERMELON_INNER, inner_points)
    else:
        # Draw right semicircle
        points = [(int(x), int(y - radius))]
        for i in range(90):
            angle = math.pi / 2 - (i * math.pi / 90)
            px = int(x + radius * math.cos(angle))
            py = int(y + radius * math.sin(angle))
            points.append((px, py))
        points.append((int(x), int(y)))
        if len(points) > 2:
            pygame.draw.polygon(surface, WATERMELON_OUTER, points)
        
        # Inner
        inner_points = [(int(x), int(y - inner_radius))]
        for i in range(90):
            angle = math.pi / 2 - (i * math.pi / 90)
            px = int(x + inner_radius * math.cos(angle))
            py = int(y + inner_radius * math.sin(angle))
            inner_points.append((px, py))
        inner_points.append((int(x), int(y)))
        if len(inner_points) > 2:
            pygame.draw.polygon(surface, WATERMELON_INNER, inner_points)


def draw_apple(surface, x, y, radius):
    """Draw an apple: red body + small brown stem."""
    # Main red body
    pygame.draw.circle(surface, APPLE_RED, (int(x), int(y)), int(radius))
    
    # Darker shade on bottom for depth
    dark_apple = (180, 20, 50)
    pygame.draw.circle(surface, dark_apple, (int(x), int(y + radius * 0.3)), int(radius * 0.6))
    
    # Stem
    stem_x, stem_y = int(x), int(y - radius)
    pygame.draw.line(surface, APPLE_STEM, (stem_x, stem_y), (stem_x, stem_y - int(radius * 0.4)), 2)
    
    # Leaf
    leaf_x = int(x + radius * 0.4)
    leaf_y = int(y - radius * 0.6)
    pygame.draw.polygon(surface, (34, 139, 34), [
        (leaf_x, leaf_y),
        (leaf_x + int(radius * 0.3), leaf_y - int(radius * 0.2)),
        (leaf_x + int(radius * 0.2), leaf_y + int(radius * 0.2))
    ])


def draw_apple_half(surface, x, y, radius, side):
    """Draw half an apple."""
    if side == "left":
        points = [(int(x), int(y - radius))]
        for i in range(90):
            angle = math.pi / 2 + (i * math.pi / 90)
            px = int(x + radius * math.cos(angle))
            py = int(y + radius * math.sin(angle))
            points.append((px, py))
        points.append((int(x), int(y)))
        if len(points) > 2:
            pygame.draw.polygon(surface, APPLE_RED, points)
    else:
        points = [(int(x), int(y - radius))]
        for i in range(90):
            angle = math.pi / 2 - (i * math.pi / 90)
            px = int(x + radius * math.cos(angle))
            py = int(y + radius * math.sin(angle))
            points.append((px, py))
        points.append((int(x), int(y)))
        if len(points) > 2:
            pygame.draw.polygon(surface, APPLE_RED, points)


def draw_orange(surface, x, y, radius):
    """Draw an orange: orange circle with segment lines."""
    pygame.draw.circle(surface, ORANGE_COLOR, (int(x), int(y)), int(radius))
    
    # Segment lines
    for angle in [0, 60, 120, 180, 240, 300]:
        rad = math.radians(angle)
        x1 = int(x + radius * math.cos(rad) * 0.6)
        y1 = int(y + radius * math.sin(rad) * 0.6)
        x2 = int(x - radius * math.cos(rad) * 0.6)
        y2 = int(y - radius * math.sin(rad) * 0.6)
        pygame.draw.line(surface, ORANGE_SEGMENT, (x1, y1), (x2, y2), 1)
    
    # Horizontal and vertical lines through center
    pygame.draw.line(surface, ORANGE_SEGMENT, (int(x - radius * 0.6), int(y)), (int(x + radius * 0.6), int(y)), 1)
    pygame.draw.line(surface, ORANGE_SEGMENT, (int(x), int(y - radius * 0.6)), (int(x), int(y + radius * 0.6)), 1)


def draw_orange_half(surface, x, y, radius, side):
    """Draw half an orange."""
    if side == "left":
        points = [(int(x), int(y - radius))]
        for i in range(90):
            angle = math.pi / 2 + (i * math.pi / 90)
            px = int(x + radius * math.cos(angle))
            py = int(y + radius * math.sin(angle))
            points.append((px, py))
        points.append((int(x), int(y)))
        if len(points) > 2:
            pygame.draw.polygon(surface, ORANGE_COLOR, points)
    else:
        points = [(int(x), int(y - radius))]
        for i in range(90):
            angle = math.pi / 2 - (i * math.pi / 90)
            px = int(x + radius * math.cos(angle))
            py = int(y + radius * math.sin(angle))
            points.append((px, py))
        points.append((int(x), int(y)))
        if len(points) > 2:
            pygame.draw.polygon(surface, ORANGE_COLOR, points)


def draw_pineapple(surface, x, y, radius):
    """Draw a pineapple: golden body + green leaves."""
    # Body (trapezoid-ish shape)
    body_width = int(radius * 1.6)
    body_height = int(radius * 2.0)
    pygame.draw.polygon(surface, PINEAPPLE_COLOR, [
        (int(x - body_width * 0.5), int(y + radius * 0.3)),
        (int(x + body_width * 0.5), int(y + radius * 0.3)),
        (int(x + body_width * 0.3), int(y + body_height * 0.5)),
        (int(x - body_width * 0.3), int(y + body_height * 0.5))
    ])
    
    # Cross-hatch pattern
    for i in range(-2, 3):
        for j in range(-2, 3):
            cx = int(x + i * radius * 0.3)
            cy = int(y + radius * 0.3 + j * radius * 0.3)
            pygame.draw.circle(surface, (184, 134, 11), (cx, cy), 2)
    
    # Leaves at top
    leaf_x1 = int(x - radius * 0.5)
    leaf_y1 = int(y - radius * 0.3)
    leaf_x2 = int(x + radius * 0.5)
    leaf_y2 = int(y - radius * 0.3)
    leaf_x_top = int(x)
    leaf_y_top = int(y - radius * 1.5)
    
    pygame.draw.polygon(surface, PINEAPPLE_LEAF, [
        (leaf_x1, leaf_y1), (leaf_x_top - int(radius * 0.15), leaf_y_top), (leaf_x1 + int(radius * 0.2), leaf_y1)
    ])
    pygame.draw.polygon(surface, PINEAPPLE_LEAF, [
        (leaf_x2, leaf_y1), (leaf_x_top + int(radius * 0.15), leaf_y_top), (leaf_x2 - int(radius * 0.2), leaf_y1)
    ])


def draw_pineapple_half(surface, x, y, radius, side):
    """Draw half a pineapple."""
    body_width = int(radius * 1.6)
    body_height = int(radius * 2.0)
    
    if side == "left":
        pygame.draw.polygon(surface, PINEAPPLE_COLOR, [
            (int(x), int(y + radius * 0.3)),
            (int(x + body_width * 0.5), int(y + radius * 0.3)),
            (int(x + body_width * 0.3), int(y + body_height * 0.5)),
            (int(x), int(y + body_height * 0.5))
        ])
    else:
        pygame.draw.polygon(surface, PINEAPPLE_COLOR, [
            (int(x - body_width * 0.5), int(y + radius * 0.3)),
            (int(x), int(y + radius * 0.3)),
            (int(x), int(y + body_height * 0.5)),
            (int(x - body_width * 0.3), int(y + body_height * 0.5))
        ])


def draw_banana(surface, x, y, radius):
    """Draw a banana: curved yellow shape."""
    points = []
    for i in range(20):
        angle = math.pi * i / 19
        bx = int(x + radius * 1.2 * math.cos(angle))
        by = int(y + radius * 0.5 * math.sin(angle) - radius * 0.3)
        points.append((bx, by))
    if len(points) >= 2:
        pygame.draw.lines(surface, (255, 220, 50), False, points, 8)
    shadow = []
    for i in range(20):
        angle = math.pi * i / 19
        bx = int(x + radius * 1.1 * math.cos(angle))
        by = int(y + radius * 0.4 * math.sin(angle) - radius * 0.25)
        shadow.append((bx, by))
    if len(shadow) >= 2:
        pygame.draw.lines(surface, (200, 160, 30), False, shadow, 3)


def draw_banana_half(surface, x, y, radius, side):
    """Draw half a banana."""
    points = []
    for i in range(20):
        angle = math.pi * i / 19
        bx = int(x + radius * 1.2 * math.cos(angle))
        by = int(y + radius * 0.5 * math.sin(angle) - radius * 0.3)
        points.append((bx, by))
    if len(points) >= 2:
        pygame.draw.lines(surface, (255, 220, 50), False, points, 8)


def draw_fruit(surface, fruit_dict):
    """
    Draw a fruit based on its type and position.
    
    fruit_dict must have:
      - "type": one of "watermelon", "apple", "orange", "pineapple", "banana"
      - "x": x coordinate
      - "y": y coordinate
      - "radius": radius of fruit
      - "sliced" (optional): boolean, if True draw halves instead
      - "side" (optional): "left" or "right" if sliced
    """
    x = fruit_dict.get("x", 0)
    y = fruit_dict.get("y", 0)
    radius = fruit_dict.get("radius", 30)
    fruit_type = fruit_dict.get("type", "watermelon")
    sliced = fruit_dict.get("sliced", False)
    side = fruit_dict.get("side", "left")
    
    if sliced:
        if fruit_type == "watermelon":
            draw_watermelon_half(surface, x, y, radius, side)
        elif fruit_type == "apple":
            draw_apple_half(surface, x, y, radius, side)
        elif fruit_type == "orange":
            draw_orange_half(surface, x, y, radius, side)
        elif fruit_type == "pineapple":
            draw_pineapple_half(surface, x, y, radius, side)
        elif fruit_type == "banana":
            draw_banana_half(surface, x, y, radius, side)
    else:
        if fruit_type == "watermelon":
            draw_watermelon(surface, x, y, radius)
        elif fruit_type == "apple":
            draw_apple(surface, x, y, radius)
        elif fruit_type == "orange":
            draw_orange(surface, x, y, radius)
        elif fruit_type == "pineapple":
            draw_pineapple(surface, x, y, radius)
        elif fruit_type == "banana":
            draw_banana(surface, x, y, radius)


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("SliceWars Fruits Test")
    clock = pygame.time.Clock()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        screen.fill((20, 20, 20))
        
        # Display whole fruits
        draw_watermelon(screen, 100, 100, 40)
        draw_apple(screen, 250, 100, 40)
        draw_orange(screen, 400, 100, 40)
        draw_pineapple(screen, 550, 100, 45)
        draw_banana(screen, 700, 120, 35)
        
        # Display sliced fruits
        draw_watermelon_half(screen, 100, 300, 40, "left")
        draw_watermelon_half(screen, 150, 300, 40, "right")
        
        draw_apple_half(screen, 250, 300, 40, "left")
        draw_apple_half(screen, 300, 300, 40, "right")
        
        draw_orange_half(screen, 400, 300, 40, "left")
        draw_orange_half(screen, 450, 300, 40, "right")
        
        draw_pineapple_half(screen, 550, 320, 45, "left")
        draw_pineapple_half(screen, 610, 320, 45, "right")
        
        draw_banana_half(screen, 700, 300, 35, "left")
        draw_banana_half(screen, 740, 300, 35, "right")
        
        # Test draw_fruit function
        test_fruit = {"type": "watermelon", "x": 400, "y": 500, "radius": 30}
        draw_fruit(screen, test_fruit)
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
