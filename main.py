import pygame
import sys
from pygame._sdl2.video import Window

BG_COLOR = (35, 35, 35)

WIDTH, HEIGHT = 800, 600
GRID_COLOR = (45, 45, 45)
GRID_COLOR_DARK = (25, 25, 25)

pygame.init()

GRID_SIZE = 15
GRID_MAJOR_EVERY = 60

CAM_POS_X = 0
CAM_POS_Y = 0


def world_to_screen(world_pos):
    return (world_pos[0] + CAM_POS_X, world_pos[1] + CAM_POS_Y)


def screen_to_world(screen_pos):
    return (screen_pos[0] - CAM_POS_X, screen_pos[1] - CAM_POS_Y)


def draw_grid(screen, width, height):
    start_world_x, start_world_y = screen_to_world((0, 0))

    # Vertical lines.
    start_x = int(start_world_x // GRID_SIZE) * GRID_SIZE
    end_x = int(start_world_x + width) + GRID_SIZE

    for world_x in range(start_x, end_x, GRID_SIZE):
        sx, _ = world_to_screen((world_x, 0))
        if 0 <= sx <= width:
            color = GRID_COLOR if world_x % GRID_MAJOR_EVERY == 0 else GRID_COLOR_DARK
            pygame.draw.line(screen, color, (sx, 0), (sx, height))

    # Horizontal lines.
    start_y = int(start_world_y // GRID_SIZE) * GRID_SIZE
    end_y = int(start_world_y + height) + GRID_SIZE

    for world_y in range(start_y, end_y, GRID_SIZE):
        _, sy = world_to_screen((0, world_y))
        if 0 <= sy <= height:
            color = GRID_COLOR if world_y % GRID_MAJOR_EVERY == 0 else GRID_COLOR_DARK
            pygame.draw.line(screen, color, (0, sy), (width, sy))


def main():
    global WIDTH, HEIGHT, CAM_POS_X, CAM_POS_Y

    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Wires Game Engine")

    sdl_window = Window.from_display_module()
    sdl_window.maximize()

    CAM_POS_X, CAM_POS_Y = WIDTH // 2, HEIGHT // 2

    panning = False
    last_mouse_pos = pygame.mouse.get_pos()

    cat_sprite = pygame.image.load("cat.png").convert_alpha()

    running = True
    while running:
        current_mouse_pos = pygame.mouse.get_pos()
        if panning:
            CAM_POS_X += current_mouse_pos[0] - last_mouse_pos[0]
            CAM_POS_Y += current_mouse_pos[1] - last_mouse_pos[1]

        last_mouse_pos = current_mouse_pos
        world_mouse = screen_to_world(current_mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2:  # Middle mouse button
                    panning = True
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    panning = False
            elif event.type == pygame.VIDEORESIZE:
                print(f"Window resized to: {event.w}x{event.h}")
                WIDTH, HEIGHT = screen.get_size()

        screen.fill(BG_COLOR)

        draw_grid(screen, WIDTH, HEIGHT)

        cat_x, cat_y = world_to_screen((0, 0))
        cat_rect = cat_sprite.get_rect(center=(int(cat_x), int(cat_y)))
        screen.blit(cat_sprite, cat_rect.topleft)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
