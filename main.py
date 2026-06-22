from typing import Optional

import pygame
import sys
from pygame._sdl2.video import Window

BG_COLOR = (35, 35, 35)

WIDTH, HEIGHT = 800, 600
GRID_COLOR = (45, 45, 45)
GRID_COLOR_DARK = (25, 25, 25)

pygame.init()

try:
    FONT = pygame.font.SysFont("Segoe UI, Tahoma, Arial", 13)
    TITLE_FONT = pygame.font.SysFont("Segoe UI, Tahoma, Arial", 14, bold=True)
    LARGE_FONT = pygame.font.SysFont("Segoe UI, Tahoma, Arial", 18, bold=True)
except:
    FONT = pygame.font.Font(None, 20)
    TITLE_FONT = pygame.font.Font(None, 22)
    LARGE_FONT = pygame.font.Font(None, 28)


GRID_SIZE = 15
GRID_MAJOR_EVERY = 60

CAM_POS: pygame.Vector2 = pygame.Vector2(0, 0)


def world_to_screen(world_pos: pygame.Vector2) -> pygame.Vector2:
    return pygame.Vector2(world_pos) + CAM_POS


def screen_to_world(screen_pos: pygame.Vector2) -> pygame.Vector2:
    return pygame.Vector2(screen_pos) - CAM_POS


def draw_text_shadow(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    pos: pygame.Vector2,
    color: tuple = (255, 255, 255),
    shadow_color: tuple = (0, 0, 0),
) -> None:
    shadow_offset = pygame.Vector2(2, 2)
    shadow_pos = pos + shadow_offset

    shadow_surf = font.render(text, True, shadow_color)
    surface.blit(shadow_surf, shadow_pos)

    text_surf = font.render(text, True, color)
    surface.blit(text_surf, pos)


class GraphNode:
    def __init__(
        self,
        x: float,
        y: float,
        title: str,
        inputs: list,
        outputs: list,
        header_color: tuple,
    ) -> None:
        self.position: pygame.Vector2 = pygame.Vector2(x, y)
        self.title: str = title
        self.header_color: tuple = header_color

        self.inputs = inputs
        self.outputs = outputs

    def pos(self) -> pygame.Vector2:
        return self.position

    def draw(self, surface: pygame.Surface) -> None:
        screen_pos = world_to_screen(self.pos())
        x, y = int(screen_pos.x), int(screen_pos.y)
        pygame.draw.rect(surface, self.header_color, (x, y, 150, 30))
        draw_text_shadow(surface, self.title, TITLE_FONT, screen_pos)

    def get_rect(self) -> pygame.Rect:
        screen_pos = world_to_screen(self.pos())
        x, y = int(screen_pos.x), int(screen_pos.y)
        return pygame.Rect(x, y, 150, 30)

    def handle_mouse(
        self, event: pygame.event.Event, world_mouse: pygame.Vector2
    ) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            wp = world_to_screen(world_mouse)
            if self.get_rect().collidepoint((int(wp.x), int(wp.y))):
                return True
        return False

    def handle_keyboard(self, event: pygame.event.Event) -> bool:
        return False


def draw_grid(screen: pygame.Surface, width: int, height: int) -> None:
    start_world = screen_to_world(pygame.Vector2(0, 0))
    start_world_x, start_world_y = start_world.x, start_world.y

    # Vertical lines.
    start_x = int(start_world_x // GRID_SIZE) * GRID_SIZE
    end_x = int(start_world_x + width) + GRID_SIZE

    for world_x in range(start_x, end_x, GRID_SIZE):
        sx_vec = world_to_screen(pygame.Vector2(world_x, 0))
        sx = int(sx_vec.x)
        if 0 <= sx <= width:
            color = GRID_COLOR if world_x % GRID_MAJOR_EVERY == 0 else GRID_COLOR_DARK
            pygame.draw.line(screen, color, (sx, 0), (sx, height))

    # Horizontal lines.
    start_y = int(start_world_y // GRID_SIZE) * GRID_SIZE
    end_y = int(start_world_y + height) + GRID_SIZE

    for world_y in range(start_y, end_y, GRID_SIZE):
        sy_vec = world_to_screen(pygame.Vector2(0, world_y))
        sy = int(sy_vec.y)
        if 0 <= sy <= height:
            color = GRID_COLOR if world_y % GRID_MAJOR_EVERY == 0 else GRID_COLOR_DARK
            pygame.draw.line(screen, color, (0, sy), (width, sy))


def main():
    global WIDTH, HEIGHT, CAM_POS

    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Wires Game Engine")

    sdl_window = Window.from_display_module()
    sdl_window.maximize()

    CAM_POS.update(WIDTH // 2, HEIGHT // 2)

    panning = False
    last_mouse_pos = pygame.mouse.get_pos()

    cat_sprite = pygame.image.load("cat.png").convert_alpha()

    node = GraphNode(100, 100, "Test Node", ["In1", "In2"], ["Out1"], (200, 50, 50))

    dragging_node: Optional[GraphNode] = None
    drag_offset = pygame.Vector2()

    clock = pygame.time.Clock()
    running = True
    while running:
        current_mouse_pos = pygame.mouse.get_pos()
        if panning:
            CAM_POS += pygame.Vector2(current_mouse_pos) - pygame.Vector2(
                last_mouse_pos
            )

        last_mouse_pos = current_mouse_pos
        world_mouse = screen_to_world(pygame.Vector2(current_mouse_pos))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2:  # Middle mouse button
                    panning = True
                elif event.button == 1:  # Left mouse button
                    if node.handle_mouse(event, world_mouse):
                        dragging_node = node
                        drag_offset = world_mouse - dragging_node.pos()
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    panning = False
                elif event.button == 1:  # Left mouse button
                    dragging_node = None
                    drag_offset.update(0, 0)
            elif event.type == pygame.MOUSEMOTION:
                if dragging_node:
                    mouse_world_pos = screen_to_world(pygame.Vector2(event.pos))
                    dragging_node.position = mouse_world_pos - drag_offset
            elif event.type == pygame.VIDEORESIZE:
                print(f"Window resized to: {event.w}x{event.h}")
                WIDTH, HEIGHT = screen.get_size()

        screen.fill(BG_COLOR)

        draw_grid(screen, WIDTH, HEIGHT)

        cat_pos = world_to_screen(pygame.Vector2(0, 0))
        cat_rect = cat_sprite.get_rect(center=(int(cat_pos.x), int(cat_pos.y)))
        screen.blit(cat_sprite, cat_rect.topleft)

        node.draw(screen)

        pygame.display.flip()

        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
