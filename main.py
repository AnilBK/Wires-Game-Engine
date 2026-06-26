from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import pygame
import sys
from pygame._sdl2.video import Window

BG_COLOR = (35, 35, 35)

WIDTH, HEIGHT = 800, 600
GRID_COLOR = (45, 45, 45)
GRID_COLOR_DARK = (25, 25, 25)

NODE_WIDTH = 180
HEADER_HEIGHT = 28
RADIUS = 10
PIN_SIDE_PADDING = 14
PIN_HOVER_HORIZONTAL_PADDING = 8

LINE_SEPARATION_COLOR = (10, 10, 10, 150)

BODY_TOP_COLOR = (60, 60, 60, 220)
BODY_BOTTOM_COLOR = (20, 20, 20, 220)

GRID_ROW_HEIGHT = 26
GRID_ROW_COLOR = (255, 255, 255, 20)

OUTER_BORDER_COLOR = (0, 0, 0, 255)
INNER_BORDER_COLOR = (255, 255, 255, 30)

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

world_cat_pos = pygame.Vector2(0, 0)

console_logs: List[str] = []


def add_console_log(log: str):
    console_logs.append(log)


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


_surface_cache = {}


def get_gradient_surface(width, height, top_color, bottom_color):
    key = ("grad", width, height, top_color, bottom_color)
    if key not in _surface_cache:
        surface = pygame.Surface((width, height), pygame.SRCALPHA)

        for y in range(height):
            t = y / (height - 1) if height > 1 else 0
            color = [
                int(top_color[i] + (bottom_color[i] - top_color[i]) * t)
                for i in range(len(top_color))
            ]
            pygame.draw.line(surface, color, (0, y), (width, y))

        _surface_cache[key] = surface
    return _surface_cache[key]


def get_rounded_rect_mask(width, height, radius):
    key = ("mask", width, height, radius)
    if key not in _surface_cache:
        mask = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(
            mask, (255, 255, 255, 255), (0, 0, width, height), border_radius=radius
        )
        _surface_cache[key] = mask
    return _surface_cache[key]


def draw_bezier(surface, start_world, end_world, color, width=3, cam_x=0, cam_y=0):
    p0 = (start_world[0] + cam_x, start_world[1] + cam_y)
    p3 = (end_world[0] + cam_x, end_world[1] + cam_y)
    dist = max(abs(p3[0] - p0[0]) * 0.6, 40)
    p1 = (p0[0] + dist, p0[1])
    p2 = (p3[0] - dist, p3[1])

    points = []
    segments = 40
    for i in range(segments + 1):
        t = i / segments
        x = (
            (1 - t) ** 3 * p0[0]
            + 3 * (1 - t) ** 2 * t * p1[0]
            + 3 * (1 - t) * t**2 * p2[0]
            + t**3 * p3[0]
        )
        y = (
            (1 - t) ** 3 * p0[1]
            + 3 * (1 - t) ** 2 * t * p1[1]
            + 3 * (1 - t) * t**2 * p2[1]
            + t**3 * p3[1]
        )
        points.append((x, y))

    shadow_points = [(px, py + 2) for px, py in points]
    pygame.draw.lines(surface, (0, 0, 0, 100), False, shadow_points, width)
    pygame.draw.lines(surface, color, False, points, width)


class PinType(Enum):
    EXEC = 0
    BOOL = 1
    INT = 2
    FLOAT = 3
    STRING = 4
    LIST = 5
    WILDCARD = 6
    VECTOR2 = 7
    VECTOR3 = 8


PinColorMap: Dict[PinType, tuple] = {
    PinType.EXEC: (255, 255, 255),
    PinType.BOOL: (149, 0, 0),
    PinType.INT: (22, 222, 185),
    PinType.FLOAT: (158, 250, 68),
    PinType.STRING: (250, 0, 208),
    PinType.LIST: (30, 144, 255),
    PinType.WILDCARD: (160, 160, 160),
    PinType.VECTOR2: (156, 224, 85),
    PinType.VECTOR3: (255, 204, 38),
}


class PinDirection(Enum):
    INPUT = 0
    OUTPUT = 1


class Pin:
    def __init__(self, name: str, pin_type: PinType) -> None:
        self.name = name
        self.pin_type: PinType = pin_type
        self.pin_direction: Optional[PinDirection] = None

        self.on_clicked: Optional[Callable[["Pin"], None]] = None
        self.node: Optional["GraphNode"] = None  # Reference to parent node.

        self.connected_pins: list[Pin] = []

        self.hovered: bool = False
        self.hover_gradient_surface = self._create_hover_gradient_surface()

    def connect_to(self, other_pin: "Pin") -> bool:
        """Attempt to connect to another pin. Return True if successful."""

        # Prevent connecting to self.
        if other_pin is self:
            return False

        # Prevent connecting input to input or output to output.
        if self.pin_direction == other_pin.pin_direction:
            return False

        # Data inputs only accept one connection.
        if self.pin_direction == PinDirection.INPUT and self.pin_type != PinType.EXEC:
            self.disconnect_all()

        if (
            other_pin.pin_direction == PinDirection.INPUT
            and other_pin.pin_type != PinType.EXEC
        ):
            other_pin.disconnect_all()

        # Apply connection bidirectionally.
        if other_pin not in self.connected_pins:
            self.connected_pins.append(other_pin)
        if self not in other_pin.connected_pins:
            other_pin.connected_pins.append(self)

        if self.node:
            self.node._build_cached_surface()

        if other_pin.node:
            other_pin.node._build_cached_surface()

        return True

    def disconnect_from(self, other_pin: "Pin") -> None:
        changed = False

        if other_pin in self.connected_pins:
            self.connected_pins.remove(other_pin)
            changed = True

        if self in other_pin.connected_pins:
            other_pin.connected_pins.remove(self)
            changed = True

        if changed:
            if self.node:
                self.node._build_cached_surface()

            if other_pin.node:
                other_pin.node._build_cached_surface()

    def disconnect_all(self) -> None:
        for other_pin in list(self.connected_pins):
            self.disconnect_from(other_pin)

    def set_direction(self, direction: PinDirection) -> None:
        self.pin_direction = direction
        self.hover_gradient_surface = self._create_hover_gradient_surface()

    def click(self) -> None:
        if self.on_clicked is not None:
            self.on_clicked(self)

    def get_icon_rect(self, pos: pygame.Vector2) -> pygame.Rect:
        if self.pin_type == PinType.EXEC:
            return pygame.Rect(int(pos.x - 8), int(pos.y - 1), 16, 14)

        return pygame.Rect(int(pos.x - 5), int(pos.y), 10, 10)

    def get_label_rect(self, pos: pygame.Vector2) -> pygame.Rect:
        if self.pin_type == PinType.EXEC:
            return pygame.Rect(0, 0, 0, 0)

        text_width, text_height = FONT.size(self.name)
        icon_center_y = self.get_icon_rect(pos).centery
        label_y = int(icon_center_y - text_height / 2)

        if self.pin_direction == PinDirection.INPUT:
            return pygame.Rect(int(pos.x + 10), label_y, text_width, text_height)

        if self.pin_direction == PinDirection.OUTPUT:
            return pygame.Rect(
                int(pos.x - text_width - 10), label_y, text_width, text_height
            )

        return pygame.Rect(0, 0, 0, 0)

    def get_rect(self, pos: pygame.Vector2) -> pygame.Rect:
        icon_rect = self.get_icon_rect(pos)
        label_rect = self.get_label_rect(pos)

        if label_rect.width == 0 or label_rect.height == 0:
            return icon_rect

        return icon_rect.union(label_rect)

    def get_hover_rect(self, pos: pygame.Vector2) -> pygame.Rect:
        return self.get_rect(pos).inflate(PIN_HOVER_HORIZONTAL_PADDING * 2, 0)

    def _create_hover_gradient_surface(self) -> pygame.Surface:
        rect = self.get_hover_rect(pygame.Vector2(0, 0))
        width = rect.width
        height = rect.height

        grad_surf = pygame.Surface((width, height), pygame.SRCALPHA)

        fade_width = 12

        self.color = PinColorMap[self.pin_type]
        r, g, b = self.color[:3]

        for x in range(width):
            if x < fade_width:
                ratio = x / fade_width
            elif x >= width - fade_width:
                ratio = (width - 1 - x) / fade_width
            else:
                ratio = 1.0

            alpha = int(90 * max(0.0, min(1.0, ratio)))

            # Fill one vertical column.
            pygame.draw.line(
                grad_surf,
                (r, g, b, alpha),
                (x, 0),
                (x, height - 1),
            )

        return grad_surf

    def draw(self, surface: pygame.Surface, pos: pygame.Vector2) -> None:
        if self.hovered:
            hover_rect = self.get_hover_rect(pos)
            surface.blit(self.hover_gradient_surface, (hover_rect.x, hover_rect.y))

        is_filled = self.hovered or bool(self.connected_pins)

        # Execute pins just have a pentagon pointing right.
        # No labels are drawn for execute pins.
        if self.pin_type == PinType.EXEC:
            x = pos.x - 7.5
            y = pos.y - 1

            points = [
                (x, y),  # top-left anchor
                (x + 8, y),  # top edge right
                (x + 15, y + 6),  # right tip
                (x + 8, y + 12),  # bottom-right
                (x, y + 12),  # bottom-left
            ]

            if is_filled:
                pygame.draw.polygon(surface, PinColorMap[self.pin_type], points)
            else:
                pygame.draw.polygon(
                    surface, PinColorMap[self.pin_type], points, width=2
                )
        else:
            # For circles, width=0 means filled, width=2 means hollow.
            circle_width = 0 if is_filled else 2

            if self.pin_direction == PinDirection.INPUT:
                pygame.draw.circle(
                    surface,
                    PinColorMap[self.pin_type],
                    (int(pos.x), int(pos.y + 5)),
                    5,
                    width=circle_width,
                )
                text_surf = FONT.render(self.name, True, (255, 255, 255))
                text_rect = text_surf.get_rect()
                text_rect.x = int(pos.x + 10)
                text_rect.centery = self.get_icon_rect(pos).centery
                surface.blit(text_surf, text_rect.topleft)
            elif self.pin_direction == PinDirection.OUTPUT:
                pygame.draw.circle(
                    surface,
                    PinColorMap[self.pin_type],
                    (int(pos.x), int(pos.y + 5)),
                    5,
                    width=circle_width,
                )
                text_surf = FONT.render(self.name, True, (255, 255, 255))
                text_rect = text_surf.get_rect()
                text_rect.x = int(pos.x - text_surf.get_width() - 10)
                text_rect.centery = self.get_icon_rect(pos).centery
                surface.blit(text_surf, text_rect.topleft)


class GraphNode:
    def __init__(
        self,
        x: float,
        y: float,
        title: str,
        header_color: tuple,
    ) -> None:
        self.position: pygame.Vector2 = pygame.Vector2(x, y)
        self.title: str = title
        self.header_color: tuple = header_color

        self.inputs: list[Pin] = []
        self.outputs: list[Pin] = []

        self.bg_surface: pygame.Surface = pygame.Surface(
            (NODE_WIDTH, HEADER_HEIGHT), pygame.SRCALPHA
        )

        self.mouse_hovered: bool = False

        self._build_cached_surface()

    def execute(self) -> Any:
        print(f"Executing node: {self.title}")

    def get_input_value(self, pin_name: str) -> Any:
        for pin in self.inputs:
            if pin.name == pin_name:
                if pin.connected_pins:
                    source_pin = pin.connected_pins[0]
                    if source_pin.node:
                        return source_pin.node.execute()
                return None
        return None

    def pos(self) -> pygame.Vector2:
        return self.position

    def _get_input_pin_pos(self, index: int) -> pygame.Vector2:
        return pygame.Vector2(
            PIN_SIDE_PADDING, HEADER_HEIGHT + index * GRID_ROW_HEIGHT + 6
        )

    def _get_output_pin_pos(self, index: int) -> pygame.Vector2:
        return pygame.Vector2(
            NODE_WIDTH - PIN_SIDE_PADDING, HEADER_HEIGHT + index * GRID_ROW_HEIGHT + 6
        )

    def get_pin_world_pos(self, pin: Pin) -> pygame.Vector2:
        if pin in self.inputs:
            index = self.inputs.index(pin)
            local_pos = self._get_input_pin_pos(index)
        elif pin in self.outputs:
            index = self.outputs.index(pin)
            local_pos = self._get_output_pin_pos(index)
        else:
            return self.pos()

        icon_rect = pin.get_icon_rect(local_pos)
        return self.pos() + pygame.Vector2(icon_rect.centerx, icon_rect.centery)

    def add_input(self, pin: Pin) -> None:
        pin.set_direction(PinDirection.INPUT)
        pin.node = self
        self.inputs.append(pin)
        self._build_cached_surface()

    def add_output(self, pin: Pin) -> None:
        pin.set_direction(PinDirection.OUTPUT)
        pin.node = self
        self.outputs.append(pin)
        self._build_cached_surface()

    def handle_events(
        self, event: pygame.event.Event, world_mouse: pygame.Vector2
    ) -> None:
        if event.type == pygame.MOUSEMOTION:
            local_mouse = world_mouse - self.pos()
            local_mouse_i_x = int(local_mouse.x)
            local_mouse_i_y = int(local_mouse.y)

            needs_rebuild = False

            for index, pin in enumerate(self.inputs):
                pin_pos = self._get_input_pin_pos(index)
                is_hovered = pin.get_rect(pin_pos).collidepoint(
                    (local_mouse_i_x, local_mouse_i_y)
                )
                if is_hovered != pin.hovered:
                    pin.hovered = is_hovered
                    needs_rebuild = True

            for index, pin in enumerate(self.outputs):
                pin_pos = self._get_output_pin_pos(index)
                is_hovered = pin.get_rect(pin_pos).collidepoint(
                    (local_mouse_i_x, local_mouse_i_y)
                )
                if is_hovered != pin.hovered:
                    pin.hovered = is_hovered
                    needs_rebuild = True

            if needs_rebuild:
                self._build_cached_surface()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            local_mouse = world_mouse - self.pos()
            local_mouse_i_x = int(local_mouse.x)
            local_mouse_i_y = int(local_mouse.y)

            for index, pin in enumerate(self.inputs):
                pin_pos = self._get_input_pin_pos(index)
                if pin.get_rect(pin_pos).collidepoint(
                    (local_mouse_i_x, local_mouse_i_y)
                ):
                    pin.click()
                    return

            for index, pin in enumerate(self.outputs):
                pin_pos = self._get_output_pin_pos(index)
                if pin.get_rect(pin_pos).collidepoint(
                    (local_mouse_i_x, local_mouse_i_y)
                ):
                    pin.click()
                    return

    def get_extra_height(self) -> int:
        return 0

    def draw_custom_content(self, surface: pygame.Surface, start_y: int) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        screen_pos = world_to_screen(self.pos())
        x, y = int(screen_pos.x), int(screen_pos.y)

        surface.blit(self.bg_surface, (x, y))

    def _build_cached_surface(self):
        max_total_items = max(len(self.inputs), len(self.outputs))

        width = NODE_WIDTH

        # Extra height for custom elements like text boxes.
        extra_height = self.get_extra_height()
        height = HEADER_HEIGHT + (max_total_items * GRID_ROW_HEIGHT) + extra_height

        content = pygame.Surface((width, height), pygame.SRCALPHA)

        # Header.
        pygame.draw.rect(
            content,
            self.header_color,
            (0, 0, width, HEADER_HEIGHT),
            border_top_left_radius=RADIUS,
            border_top_right_radius=RADIUS,
        )

        draw_text_shadow(content, self.title, TITLE_FONT, pygame.Vector2(10, 6))

        # Horizontal line separating header from body.
        pygame.draw.line(
            content,
            LINE_SEPARATION_COLOR,
            (0, HEADER_HEIGHT),
            (width, HEADER_HEIGHT),
            2,
        )

        # Body gradient.
        body_height = height - HEADER_HEIGHT
        body_gradient = get_gradient_surface(
            width, body_height, BODY_TOP_COLOR, BODY_BOTTOM_COLOR
        )
        content.blit(body_gradient, (0, HEADER_HEIGHT))

        # Currently drawing lines for input and output pins.
        # TODO: Render the pins themselves and their labels.
        y = HEADER_HEIGHT
        for _ in range(max_total_items):
            pygame.draw.line(content, GRID_ROW_COLOR, (0, y), (width, y))
            y += GRID_ROW_HEIGHT

        for index, pin in enumerate(self.inputs):
            pin_pos = self._get_input_pin_pos(index)
            pin.draw(content, pin_pos)

        for index, pin in enumerate(self.outputs):
            pin_pos = self._get_output_pin_pos(index)
            pin.draw(content, pin_pos)

        self.draw_custom_content(
            content, HEADER_HEIGHT + max_total_items * GRID_ROW_HEIGHT
        )

        # Rounded rect mask to clip all rendered content to a rounded rectangle shape.
        rounded_rect_mask = get_rounded_rect_mask(width, height, RADIUS)
        content.blit(rounded_rect_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        # Outer border.
        pygame.draw.rect(
            content,
            OUTER_BORDER_COLOR,
            (0, 0, width, height),
            width=1,
            border_radius=RADIUS,
        )

        # Inner very transparent white border for a subtle highlight effect.
        pygame.draw.rect(
            content,
            INNER_BORDER_COLOR,
            (1, 1, width - 2, height - 2),
            width=1,
            border_radius=RADIUS - 1,
        )

        self.bg_surface = content

    def get_rect(self) -> pygame.Rect:
        screen_pos = world_to_screen(self.pos())
        x, y = int(screen_pos.x), int(screen_pos.y)
        return pygame.Rect(x, y, NODE_WIDTH, HEADER_HEIGHT)

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


class MakeVector2Node(GraphNode):
    def execute(self):
        x_val = self.get_input_value("input_x")
        y_val = self.get_input_value("input_y")

        add_console_log(str(x_val))
        add_console_log(str(y_val))

        try:
            x = float(x_val) if x_val is not None and x_val != "" else 0.0
        except ValueError:
            x = 0.0

        try:
            y = float(y_val) if y_val is not None and y_val != "" else 0.0
        except ValueError:
            y = 0.0

        return pygame.Vector2(x, y)


class StringConstantNode(GraphNode):
    def execute(self):
        return "Hello World from StringConstantNode!"


class SetPositionNode(GraphNode):
    def execute(self):
        vector2_input = self.get_input_value("input_vec")
        if vector2_input is not None:
            global world_cat_pos
            world_cat_pos.update(vector2_input)
        else:
            add_console_log("input_vec is empty.")


class PrintNode(GraphNode):
    def execute(self):
        string_value = self.get_input_value("String")
        if string_value is not None:
            add_console_log(f"PrintNode: {string_value}")
        else:
            add_console_log("Hello World from PrintNode!")


class TextInputNode(GraphNode):
    def init_pins(self):
        self.add_output(Pin("Text", PinType.STRING))

    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        self.text: str = ""
        self.active: bool = False
        super().__init__(x, y, title, header_color)

        self.init_pins()

    def execute(self):
        return self.text

    def get_extra_height(self) -> int:
        return 34

    def handle_events(
        self, event: pygame.event.Event, world_mouse: pygame.Vector2
    ) -> None:
        super().handle_events(event, world_mouse)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            local_mouse = world_mouse - self.pos()
            max_total_items = max(len(self.inputs), len(self.outputs))
            box_rect = pygame.Rect(
                10,
                HEADER_HEIGHT + max_total_items * GRID_ROW_HEIGHT + 5,
                NODE_WIDTH - 20,
                24,
            )

            if box_rect.collidepoint(local_mouse.x, local_mouse.y):
                self.active = True
                self._build_cached_surface()
            else:
                if self.active:
                    self.active = False
                    self._build_cached_surface()
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
            self._build_cached_surface()

    def draw_custom_content(self, surface: pygame.Surface, start_y: int) -> None:
        box_rect = pygame.Rect(10, start_y + 5, NODE_WIDTH - 20, 24)
        color = (80, 80, 80) if self.active else (40, 40, 40)

        pygame.draw.rect(surface, color, box_rect, border_radius=4)
        pygame.draw.rect(
            surface,
            (150, 150, 150) if self.active else (100, 100, 100),
            box_rect,
            width=1,
            border_radius=4,
        )

        text_surf = FONT.render(self.text, True, (255, 255, 255))

        # Keep text inside the box
        old_clip = surface.get_clip()
        surface.set_clip(box_rect.inflate(-8, -4))

        text_w = text_surf.get_width()
        box_w = box_rect.width - 8
        offset_x = 0
        if text_w > box_w and self.active:
            offset_x = box_w - text_w

        surface.blit(text_surf, (box_rect.x + 4 + offset_x, box_rect.y + 4))
        surface.set_clip(old_clip)


class FloatInputNode(TextInputNode):
    def init_pins(self):
        self.add_output(Pin("value", PinType.FLOAT))


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

    begin_play_node = GraphNode(100, 100, "Event BeginPlay", (200, 50, 50))
    begin_play_exec_right_pin = Pin("Exec Right", PinType.EXEC)
    begin_play_node.add_output(begin_play_exec_right_pin)

    print_node = PrintNode(400, 100, "Print Hello World", (50, 200, 50))
    print_node_exec_left_pin = Pin("Exec Left", PinType.EXEC)
    print_node.add_input(print_node_exec_left_pin)
    print_node_string_pin = Pin("String", PinType.STRING)
    print_node.add_input(print_node_string_pin)
    print_node_exec_right_pin = Pin("Exec Right", PinType.EXEC)
    print_node.add_output(print_node_exec_right_pin)

    hello_world_node = StringConstantNode(100, 400, "Hello World", (50, 50, 200))
    hello_world_string_pin = Pin("String", PinType.STRING)
    hello_world_node.add_output(hello_world_string_pin)

    text_input_node = TextInputNode(100, 300, "Text Input", (150, 50, 150))

    x_node = FloatInputNode(-300, 100, "X", (150, 150, 150))
    y_node = FloatInputNode(-300, 280, "Y", (150, 150, 150))

    make_vector2_node = MakeVector2Node(100, 200, "Make Vector2 Node", (200, 50, 50))
    make_vector2_node_input_x_pin = Pin("input_x", PinType.FLOAT)
    make_vector2_node_input_y_pin = Pin("input_y", PinType.FLOAT)
    make_vector2_node.add_input(make_vector2_node_input_x_pin)
    make_vector2_node.add_input(make_vector2_node_input_y_pin)
    make_vector2_node_output_pin = Pin("output_vec", PinType.VECTOR2)
    make_vector2_node.add_output(make_vector2_node_output_pin)

    set_pos_node = SetPositionNode(400, 200, "Set Cat Position", (200, 200, 50))
    set_pos_exec_left_pin = Pin("Exec Left", PinType.EXEC)
    set_pos_node.add_input(set_pos_exec_left_pin)
    set_pos_node_in_vec2_node = Pin("input_vec", PinType.VECTOR2)
    set_pos_node.add_input(set_pos_node_in_vec2_node)
    set_pos_exec_right_pin = Pin("Exec Right", PinType.EXEC)
    set_pos_node.add_output(set_pos_exec_right_pin)

    clicked_pin: Optional[Pin] = None

    def on_pin_clicked(pin: Pin) -> None:
        nonlocal clicked_pin
        clicked_pin = pin
        node_name = pin.node.title if pin.node else "Unknown Node"
        print(f"Pin clicked: {pin.name} on {node_name}")

    graph: list[GraphNode] = [
        begin_play_node,
        print_node,
        hello_world_node,
        text_input_node,
        set_pos_node,
        x_node,
        y_node,
        make_vector2_node,
    ]

    for node in graph:
        for pin in (*node.inputs, *node.outputs):
            pin.on_clicked = on_pin_clicked

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
                    for node in reversed(
                        graph
                    ):  # Check nodes in reverse order for proper z-index
                        if node.handle_mouse(event, world_mouse):
                            dragging_node = node
                            drag_offset = world_mouse - dragging_node.pos()
                            break
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    panning = False
                elif event.button == 1:  # Left mouse button
                    dragging_node = None
                    drag_offset.update(0, 0)

                    # If we were dragging a wire...
                    if clicked_pin:
                        # Check if we dropped it on another pin
                        dropped_on_pin = None
                        for node in graph:
                            for pin in (*node.inputs, *node.outputs):
                                pin_pos = node.get_pin_world_pos(pin)
                                screen_pin_pos = world_to_screen(pin_pos)

                                # Simple radius check to see if mouse is over the pin
                                if (
                                    pygame.Vector2(event.pos).distance_to(
                                        screen_pin_pos
                                    )
                                    < 15
                                ):
                                    dropped_on_pin = pin
                                    break
                            if dropped_on_pin:
                                break

                        if dropped_on_pin:
                            success = clicked_pin.connect_to(dropped_on_pin)
                            if success:
                                print(
                                    f"Connected {clicked_pin.name} to {dropped_on_pin.name}"
                                )
                            else:
                                print("Invalid connection!")

                        clicked_pin = None  # Clear dragged wire
            elif event.type == pygame.MOUSEMOTION:
                if dragging_node:
                    mouse_world_pos = screen_to_world(pygame.Vector2(event.pos))
                    dragging_node.position = mouse_world_pos - drag_offset
            elif event.type == pygame.VIDEORESIZE:
                print(f"Window resized to: {event.w}x{event.h}")
                WIDTH, HEIGHT = screen.get_size()

            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]:
                if clicked_pin:
                    clicked_pin = None
                    print("Wire drawing canceled.")
            elif keys[pygame.K_KP_ENTER] or keys[pygame.K_RETURN]:
                print("Executing test VM...")

                def execute_node_chain(node: GraphNode, visited=None):
                    if visited is None:
                        visited = set()

                    if id(node) in visited:
                        return

                    visited.add(id(node))

                    node.execute()

                    for output_pin in node.outputs:
                        if output_pin.pin_type == PinType.EXEC:
                            for connected_pin in output_pin.connected_pins:
                                if (
                                    connected_pin.pin_type == PinType.EXEC
                                    and connected_pin.node
                                ):
                                    print(
                                        f"Executing node: {connected_pin.node.title} via pin: {connected_pin.name}"
                                    )
                                    execute_node_chain(connected_pin.node, visited)

                execute_node_chain(begin_play_node)

                print("Execution chain complete.")

            for node in graph:
                node.handle_events(event, world_mouse)

        screen.fill(BG_COLOR)

        draw_grid(screen, WIDTH, HEIGHT)

        cat_pos = world_to_screen(world_cat_pos)

        cat_rect = cat_sprite.get_rect(center=(int(cat_pos.x), int(cat_pos.y)))
        screen.blit(cat_sprite, cat_rect.topleft)

        # Draw all connections.
        for node in graph:
            for pin in node.outputs:
                # Only iterate outputs to prevent drawing lines twice.
                for connected_pin in pin.connected_pins:
                    start_pos = world_to_screen(node.get_pin_world_pos(pin))
                    end_pos = world_to_screen(
                        connected_pin.node.get_pin_world_pos(connected_pin)
                    )

                    wire_color = PinColorMap[pin.pin_type]

                    draw_bezier(screen, start_pos, end_pos, wire_color, width=3)

        for node in graph:
            node.draw(screen)

        # Draw a line from the clicked pin to the current mouse position.
        if clicked_pin and clicked_pin.node:
            pin_world_pos = clicked_pin.node.get_pin_world_pos(clicked_pin)
            start_pos = world_to_screen(pin_world_pos)
            end_pos = pygame.Vector2(current_mouse_pos)

            wire_color = PinColorMap[clicked_pin.pin_type]
            draw_bezier(screen, start_pos, end_pos, wire_color, width=3)

        log_pos = pygame.Vector2(20, 20)
        for i, log in enumerate(console_logs):
            text_surf = TITLE_FONT.render(log, True, (220, 200, 10))
            screen.blit(text_surf, log_pos + pygame.Vector2(0, i * 20))

        pygame.display.flip()

        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
