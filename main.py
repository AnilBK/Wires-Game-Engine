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


def draw_grid(screen, cam_x, cam_y, width, height):
    start_world_x, start_world_y = -cam_x, -cam_y

    # Vertical lines.
    start_x = int(start_world_x // GRID_SIZE) * GRID_SIZE
    end_x = int(start_world_x + width) + GRID_SIZE

    for world_x in range(start_x, end_x, GRID_SIZE):
        sx = world_x + cam_x
        if 0 <= sx <= width:
            color = GRID_COLOR if world_x % GRID_MAJOR_EVERY == 0 else GRID_COLOR_DARK
            pygame.draw.line(screen, color, (sx, 0), (sx, height))

    # Horizontal lines.
    start_y = int(start_world_y // GRID_SIZE) * GRID_SIZE
    end_y = int(start_world_y + height) + GRID_SIZE

    for world_y in range(start_y, end_y, GRID_SIZE):
        sy = world_y + cam_y
        if 0 <= sy <= height:
            color = GRID_COLOR if world_y % GRID_MAJOR_EVERY == 0 else GRID_COLOR_DARK
            pygame.draw.line(screen, color, (0, sy), (width, sy))


def main():
    global WIDTH, HEIGHT

    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Wires Game Engine")

    sdl_window = Window.from_display_module()
    sdl_window.maximize()

    cam_x, cam_y = WIDTH // 2, HEIGHT // 2

    panning = False
    last_mouse_pos = pygame.mouse.get_pos()

    running = True
    while running:
        current_mouse_pos = pygame.mouse.get_pos()
        if panning:
            cam_x += current_mouse_pos[0] - last_mouse_pos[0]
            cam_y += current_mouse_pos[1] - last_mouse_pos[1]

        last_mouse_pos = current_mouse_pos
        world_mouse = (current_mouse_pos[0] - cam_x, current_mouse_pos[1] - cam_y)

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

        draw_grid(screen, cam_x, cam_y, WIDTH, HEIGHT)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
