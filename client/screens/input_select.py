# client/screens/input_select.py
# Pygame screen for selecting the player's input method at launch.

import pygame

WIDTH = 800
HEIGHT = 600
BUTTON_WIDTH = 320
BUTTON_HEIGHT = 80
BUTTON_SPACING = 30
TITLE_FONT_SIZE = 64
BUTTON_FONT_SIZE = 36

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_GRAY = (40, 40, 40)
LIGHT_GRAY = (200, 200, 200)
BLUE = (50, 115, 220)
HOVER_BLUE = (70, 135, 240)


def draw_text(surface, text, font, color, center):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=center)
    surface.blit(rendered, rect)


class Button:
    def __init__(self, rect, text, font):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font

    def draw(self, surface, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        color = HOVER_BLUE if hovered else BLUE
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        draw_text(surface, self.text, self.font, WHITE, self.rect.center)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


def run(screen=None):
    pygame.init()
    if screen is None:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('SliceWars')

    title_font = pygame.font.SysFont(None, TITLE_FONT_SIZE)
    button_font = pygame.font.SysFont(None, BUTTON_FONT_SIZE)
    clock = pygame.time.Clock()

    button_x = (WIDTH - BUTTON_WIDTH) // 2
    button_y = 220
    button_a = Button((button_x, button_y, BUTTON_WIDTH, BUTTON_HEIGHT), 'Play with Webcam', button_font)
    button_b = Button((button_x, button_y + BUTTON_HEIGHT + BUTTON_SPACING, BUTTON_WIDTH, BUTTON_HEIGHT), 'Play with Mouse', button_font)

    choice = None
    running = True

    while running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif button_a.is_clicked(event):
                choice = 'webcam'
                running = False
            elif button_b.is_clicked(event):
                choice = 'mouse'
                running = False

        screen.fill(WHITE)
        draw_text(screen, 'SliceWars', title_font, BLACK, (WIDTH // 2, 90))
        button_a.draw(screen, mouse_pos)
        button_b.draw(screen, mouse_pos)

        pygame.display.flip()
        clock.tick(60)

    return choice
if __name__ == "__main__":
    result = run()
    print(f"Player chose: {result}")
