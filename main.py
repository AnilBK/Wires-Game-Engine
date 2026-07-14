from collections import deque
from dataclasses import dataclass
from enum import Enum

import time
from typing import Any, Callable, Dict, List, Optional
import types

import pygame
import sys
from pygame._sdl2.video import Window

from game_object import Scene, Sprite

BG_COLOR = (35, 35, 35)

WIDTH, HEIGHT = 800, 600
GRID_COLOR = (45, 45, 45)
GRID_COLOR_DARK = (25, 25, 25)

MIN_NODE_WIDTH = 180
HEADER_HEIGHT = 28
RADIUS = 10
PIN_SIDE_PADDING = 14
PIN_HOVER_HORIZONTAL_PADDING = 8

LINE_SEPARATION_COLOR = (10, 10, 10, 150)

BODY_TOP_COLOR = (60, 60, 60, 220)
BODY_BOTTOM_COLOR = (20, 20, 20, 220)

GRID_ROW_HEIGHT = 28
GRID_ROW_COLOR = (255, 255, 255, 20)

OUTER_BORDER_COLOR = (0, 0, 0, 255)
INNER_BORDER_COLOR = (255, 255, 255, 30)

pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Wires Game Engine")

sdl_window = Window.from_display_module()
sdl_window.maximize()

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


scene = Scene("cat_scene")

scene.RegisterNode(
    Sprite(
        identifier="cat",
        texture="cat.png",
    )
)

cat1 = scene.Instantiate("cat")
cat1.SetPosition(pygame.Vector2(100, 100))

# cat2 = scene.Instantiate("cat")
# cat2.SetPosition(pygame.Vector2(300, 150))

# cat3 = scene.Instantiate("cat")
# cat3.SetPosition(pygame.Vector2(500, 250))

cat = cat1


@dataclass
class ConsoleLog:
    ts: float
    log: str


console_logs = deque()


def add_console_log(log: str):
    console_logs.append(ConsoleLog(time.time(), log))


def clear_expired_logs():
    now = time.time()
    while console_logs and now - console_logs[0].ts >= 5.0:
        console_logs.popleft()


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
    GAMEOBJECT = 9


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
    PinType.GAMEOBJECT: (255, 128, 0),
}


class PinDirection(Enum):
    INPUT = 0
    OUTPUT = 1


class PinUIComponent:
    def __init__(self):
        self.pin = None

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        pass

    def handle_event(
        self, event: pygame.event.Event, local_mouse: pygame.Vector2, rect: pygame.Rect
    ) -> bool:
        """Returns True if the node's cached surface needs a rebuild"""
        return False

    def get_value(self) -> Any:
        return None


class TextBoxComponent(PinUIComponent):
    def __init__(self, initial_text: str = "", cast_type: Optional[type] = str):
        super().__init__()
        self.text = str(initial_text)
        self.active = False
        self.cast_type = cast_type

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        color = (80, 80, 80) if self.active else (40, 40, 40)
        pygame.draw.rect(surface, color, rect, border_radius=4)
        pygame.draw.rect(
            surface,
            (150, 150, 150) if self.active else (100, 100, 100),
            rect,
            width=1,
            border_radius=4,
        )

        text_surf = FONT.render(self.text, True, (255, 255, 255))
        old_clip = surface.get_clip()
        surface.set_clip(rect.inflate(-4, -4))

        text_w = text_surf.get_width()
        box_w = rect.width - 6
        offset_x = 0

        if text_w > box_w and self.active:
            offset_x = box_w - text_w

        surface.blit(
            text_surf,
            (
                rect.x + 4 + offset_x,
                rect.y + (rect.height - text_surf.get_height()) // 2,
            ),
        )
        surface.set_clip(old_clip)

    def handle_event(
        self, event: pygame.event.Event, local_mouse: pygame.Vector2, rect: pygame.Rect
    ) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if rect.collidepoint(local_mouse.x, local_mouse.y):
                if not self.active:
                    self.active = True
                    return True
            else:
                if self.active:
                    self.active = False
                    return True
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
            return True
        return False

    def get_value(self) -> Any:
        if self.text == "":
            return self.cast_type() if self.cast_type else None
        if self.cast_type:
            try:
                return self.cast_type(self.text)
            except ValueError:
                return self.cast_type()
        return self.text


class BoolToggleComponent(PinUIComponent):
    def __init__(self, initial_value: bool = False):
        super().__init__()
        self.value = initial_value

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        color = (30, 110, 50) if self.value else (120, 30, 30)
        pygame.draw.rect(surface, color, rect, border_radius=4)
        pygame.draw.rect(surface, (180, 180, 180), rect, width=1, border_radius=4)

        text = "TRUE" if self.value else "FALSE"
        text_surf = FONT.render(text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect.topleft)

    def handle_event(
        self, event: pygame.event.Event, local_mouse: pygame.Vector2, rect: pygame.Rect
    ) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if rect.collidepoint(local_mouse.x, local_mouse.y):
                self.value = not self.value
                return True
        return False

    def get_value(self) -> bool:
        return self.value


class Pin:
    def __init__(
        self,
        name: str,
        pin_type: PinType,
        ui_component: Optional[PinUIComponent] = None,
    ) -> None:
        self.name = name
        self.pin_type: PinType = pin_type
        self.pin_direction: Optional[PinDirection] = None

        self.on_clicked: Optional[Callable[["Pin"], None]] = None
        self.node: Optional["GraphNode"] = None  # Reference to parent node.

        self.connected_pins: list[Pin] = []

        self.hovered: bool = False
        self.hover_gradient_surface = self._create_hover_gradient_surface()

        self.ui_component = ui_component
        if self.ui_component:
            self.ui_component.pin = self

    def connect_to(self, other_pin: "Pin") -> bool:
        """Attempt to connect to another pin. Return True if successful."""

        # Prevent connecting to self.
        if other_pin is self:
            return False

        # Prevent connecting input to input or output to output.
        if self.pin_direction == other_pin.pin_direction:
            return False

        if self.pin_type == PinType.EXEC and self.pin_direction == PinDirection.OUTPUT:
            self.disconnect_all()

        if (
            other_pin.pin_type == PinType.EXEC
            and other_pin.pin_direction == PinDirection.OUTPUT
        ):
            other_pin.disconnect_all()

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

    def get_ui_rect(self, pos: pygame.Vector2) -> pygame.Rect:
        label_rect = self.get_label_rect(pos)
        ui_height = 20
        ui_y = int(self.get_icon_rect(pos).centery - ui_height / 2)

        node_width = self.node.width if self.node else MIN_NODE_WIDTH

        if self.pin_direction == PinDirection.INPUT:
            x = label_rect.right + 10
            right_bound = node_width - PIN_SIDE_PADDING

            # Find the component on the right side in the same row to establish the right boundary.
            if self.node and self in self.node.inputs:
                idx = self.node.inputs.index(self)
                if idx < len(self.node.outputs):
                    out_pin = self.node.outputs[idx]
                    out_pos = self.node._get_output_pin_pos(idx)
                    out_rect = out_pin.get_rect(out_pos)
                    right_bound = out_rect.left - 10

            width = max(20, right_bound - x)
            return pygame.Rect(x, ui_y, width, ui_height)
        elif self.pin_direction == PinDirection.OUTPUT:
            right_bound = label_rect.left - 10
            left_bound = PIN_SIDE_PADDING

            # Find the component on the left side in the same row to establish the left boundary.
            if self.node and self in self.node.outputs:
                idx = self.node.outputs.index(self)
                if idx < len(self.node.inputs):
                    in_pin = self.node.inputs[idx]
                    in_pos = self.node._get_input_pin_pos(idx)
                    in_rect = in_pin.get_rect(in_pos)
                    left_bound = in_rect.right + 10

            width = max(20, right_bound - left_bound)
            x = left_bound
            return pygame.Rect(x, ui_y, width, ui_height)

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

        # Draw UI Component if unconnected or if it's an output pin.
        if self.ui_component and (
            self.pin_direction == PinDirection.OUTPUT or not self.connected_pins
        ):
            self.ui_component.draw(surface, self.get_ui_rect(pos))

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

        self.width = MIN_NODE_WIDTH

        self.inputs: list[Pin] = []
        self.outputs: list[Pin] = []

        self.bg_surface: pygame.Surface = pygame.Surface(
            (self.width, HEADER_HEIGHT), pygame.SRCALPHA
        )

        self.mouse_hovered: bool = False

    def get_input_value(self, pin_name: str) -> Any:
        for pin in self.inputs:
            if pin.name == pin_name:
                if pin.connected_pins:
                    source_pin = pin.connected_pins[0]
                    if source_pin.node:
                        return source_pin.node.get_output_value(source_pin.name)
                # Fallback to UI Component value if available.
                if pin.ui_component:
                    return pin.ui_component.get_value()
                return None
        return None

    def evaluate(self, pin_name: str) -> Any:
        """Data nodes like Math/String nodes override it to return data."""
        return None

    def execute(self, triggered_pin: Optional[Pin] = None):
        """Control nodes override it to perform actions."""
        # By default, we just pass the execution to the next node.
        yield from self.trigger_out_pin()

    def get_output_value(self, pin_name: str) -> Any:
        return self.evaluate(pin_name)

    def trigger_out_pin(self, pin_name: Optional[str] = None):
        target_pin = None
        if pin_name:
            target_pin = self.get_output_pin(pin_name)
        else:
            for pin in self.outputs:
                if pin.pin_type == PinType.EXEC:
                    target_pin = pin
                    break

        if target_pin:
            for connected_pin in target_pin.connected_pins:
                if connected_pin.node:
                    yield from connected_pin.node.execute(connected_pin)

    def get_output_pin(self, name: str) -> Optional[Pin]:
        for pin in self.outputs:
            if pin.name == name:
                return pin
        return None

    def get_input_pin(self, name: str) -> Optional[Pin]:
        for pin in self.inputs:
            if pin.name == name:
                return pin
        return None

    def pos(self) -> pygame.Vector2:
        return self.position

    def calculate_width(self) -> int:
        width = MIN_NODE_WIDTH
        title_width = TITLE_FONT.size(self.title)[0] + 60
        width = max(width, title_width)

        max_rows = max(len(self.inputs), len(self.outputs))
        for i in range(max_rows):
            left_w = PIN_SIDE_PADDING
            right_w = PIN_SIDE_PADDING

            # Calculate space needed by the left pin.
            if i < len(self.inputs):
                pin = self.inputs[i]
                if pin.pin_type == PinType.EXEC:
                    left_w += 20
                else:
                    left_w += 15 + FONT.size(pin.name)[0]
                if pin.ui_component and (
                    pin.pin_direction == PinDirection.OUTPUT or not pin.connected_pins
                ):
                    ui_w = 60
                    if hasattr(pin.ui_component, "text"):
                        ui_w = max(60, FONT.size(pin.ui_component.text)[0] + 16)
                    left_w += 10 + ui_w

            # Calculate space needed by the right pin.
            if i < len(self.outputs):
                pin = self.outputs[i]
                if pin.pin_type == PinType.EXEC:
                    right_w += 20
                else:
                    right_w += 15 + FONT.size(pin.name)[0]
                if pin.ui_component and (
                    pin.pin_direction == PinDirection.OUTPUT or not pin.connected_pins
                ):
                    ui_w = 60
                    if hasattr(pin.ui_component, "text"):
                        ui_w = max(60, FONT.size(pin.ui_component.text)[0] + 16)
                    right_w += 10 + ui_w

            row_width = left_w + right_w + 30
            width = max(width, row_width)

        return width

    def _get_input_pin_pos(self, index: int) -> pygame.Vector2:
        return pygame.Vector2(
            PIN_SIDE_PADDING, HEADER_HEIGHT + index * GRID_ROW_HEIGHT + 6
        )

    def _get_output_pin_pos(self, index: int) -> pygame.Vector2:
        return pygame.Vector2(
            self.width - PIN_SIDE_PADDING, HEADER_HEIGHT + index * GRID_ROW_HEIGHT + 6
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
        local_mouse = world_mouse - self.pos()
        local_mouse_i_x = int(local_mouse.x)
        local_mouse_i_y = int(local_mouse.y)
        needs_rebuild = False
        ui_handled = False

        for i, pin in enumerate(self.inputs):
            if pin.ui_component and (
                pin.pin_direction == PinDirection.OUTPUT or not pin.connected_pins
            ):
                ui_rect = pin.get_ui_rect(self._get_input_pin_pos(i))
                if pin.ui_component.handle_event(event, local_mouse, ui_rect):
                    needs_rebuild = True
                    ui_handled = True

        for i, pin in enumerate(self.outputs):
            if pin.ui_component and (
                pin.pin_direction == PinDirection.OUTPUT or not pin.connected_pins
            ):
                ui_rect = pin.get_ui_rect(self._get_output_pin_pos(i))
                if pin.ui_component.handle_event(event, local_mouse, ui_rect):
                    needs_rebuild = True
                    ui_handled = True

        if event.type == pygame.MOUSEMOTION:
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

        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and not ui_handled
        ):
            alt_pressed = bool(pygame.key.get_mods() & pygame.KMOD_ALT)

            for index, pin in enumerate(self.inputs):
                pin_pos = self._get_input_pin_pos(index)
                if pin.get_rect(pin_pos).collidepoint(
                    (local_mouse_i_x, local_mouse_i_y)
                ):
                    if alt_pressed:
                        pin.disconnect_all()
                    else:
                        pin.click()
                    return

            for index, pin in enumerate(self.outputs):
                pin_pos = self._get_output_pin_pos(index)
                if pin.get_rect(pin_pos).collidepoint(
                    (local_mouse_i_x, local_mouse_i_y)
                ):
                    if alt_pressed:
                        pin.disconnect_all()
                    else:
                        pin.click()
                    return

        if needs_rebuild:
            self._build_cached_surface()

    def get_extra_height(self) -> int:
        return 0

    def draw_custom_content(self, surface: pygame.Surface, start_y: int) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        screen_pos = world_to_screen(self.pos())
        x, y = int(screen_pos.x), int(screen_pos.y)

        surface.blit(self.bg_surface, (x, y))

    def _build_cached_surface(self):
        self.width = self.calculate_width()
        max_total_items = max(len(self.inputs), len(self.outputs))

        # Extra height for custom elements like text boxes.
        extra_height = self.get_extra_height()
        height = HEADER_HEIGHT + (max_total_items * GRID_ROW_HEIGHT) + extra_height

        content = pygame.Surface((self.width, height), pygame.SRCALPHA)

        # Header.
        pygame.draw.rect(
            content,
            self.header_color,
            (0, 0, self.width, HEADER_HEIGHT),
            border_top_left_radius=RADIUS,
            border_top_right_radius=RADIUS,
        )

        draw_text_shadow(content, self.title, TITLE_FONT, pygame.Vector2(10, 6))

        # Horizontal line separating header from body.
        pygame.draw.line(
            content,
            LINE_SEPARATION_COLOR,
            (0, HEADER_HEIGHT),
            (self.width, HEADER_HEIGHT),
            2,
        )

        # Body gradient.
        body_height = height - HEADER_HEIGHT
        body_gradient = get_gradient_surface(
            self.width, body_height, BODY_TOP_COLOR, BODY_BOTTOM_COLOR
        )
        content.blit(body_gradient, (0, HEADER_HEIGHT))

        # Currently drawing lines for input and output pins.
        y = HEADER_HEIGHT
        for _ in range(max_total_items):
            pygame.draw.line(content, GRID_ROW_COLOR, (0, y), (self.width, y))
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
        rounded_rect_mask = get_rounded_rect_mask(self.width, height, RADIUS)
        content.blit(rounded_rect_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        # Outer border.
        pygame.draw.rect(
            content,
            OUTER_BORDER_COLOR,
            (0, 0, self.width, height),
            width=1,
            border_radius=RADIUS,
        )

        # Inner very transparent white border for a subtle highlight effect.
        pygame.draw.rect(
            content,
            INNER_BORDER_COLOR,
            (1, 1, self.width - 2, height - 2),
            width=1,
            border_radius=RADIUS - 1,
        )

        self.bg_surface = content

    def get_rect(self) -> pygame.Rect:
        screen_pos = world_to_screen(self.pos())
        x, y = int(screen_pos.x), int(screen_pos.y)
        return pygame.Rect(x, y, self.width, HEADER_HEIGHT)

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

    def is_editing_ui(self) -> bool:
        for pin in self.inputs + self.outputs:
            if (
                isinstance(pin.ui_component, TextBoxComponent)
                and pin.ui_component.active
            ):
                return True
        return False


class MakeVector2Node(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(
            Pin("input_x", PinType.FLOAT, ui_component=TextBoxComponent("0.0", float))
        )
        self.add_input(
            Pin("input_y", PinType.FLOAT, ui_component=TextBoxComponent("0.0", float))
        )
        self.add_output(Pin("output_vec", PinType.VECTOR2))
        self._build_cached_surface()

    def evaluate(self, pin_name: str):
        x_val = self.get_input_value("input_x")
        y_val = self.get_input_value("input_y")
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
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.ui_comp = TextBoxComponent("Hello World", str)
        self.add_output(Pin("String", PinType.STRING, ui_component=self.ui_comp))
        self._build_cached_surface()

    def evaluate(self, pin_name: str):
        return self.ui_comp.get_value()


class SetPositionNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_input(Pin("input_vec", PinType.VECTOR2))
        self.add_output(Pin("Exec Right", PinType.EXEC))
        self._build_cached_surface()

    def execute(self, triggered_pin: Optional[Pin] = None):
        vector2_input = self.get_input_value("input_vec")
        if vector2_input is not None:
            global cat
            cat.SetPosition(vector2_input)
        else:
            add_console_log("input_vec is empty.")

        yield from self.trigger_out_pin("Exec Right")


class PrintNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_input(
            Pin(
                "String",
                PinType.STRING,
                ui_component=TextBoxComponent("Hello World", str),
            )
        )
        self.add_output(Pin("Exec Right", PinType.EXEC))
        self._build_cached_surface()

    def execute(self, triggered_pin: Optional[Pin] = None):
        string_value = self.get_input_value("String")
        if string_value is not None:
            add_console_log(f"PrintNode: {string_value}")
        else:
            add_console_log("Hello World from PrintNode!")

        yield from self.trigger_out_pin("Exec Right")


class TextInputNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        self.text: str = "Input text"
        self.active: bool = False
        super().__init__(x, y, title, header_color)

        self.add_output(Pin("Text", PinType.STRING))

    def calculate_width(self) -> int:
        base_width = super().calculate_width()
        custom_text_w = FONT.size(self.text)[0] + 30
        return max(base_width, custom_text_w)

    def evaluate(self, pin_name: str):
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

            box_width = self.width - 20
            box_rect = pygame.Rect(
                10, HEADER_HEIGHT + max_total_items * GRID_ROW_HEIGHT + 5, box_width, 24
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
        box_width = self.width - 20
        box_rect = pygame.Rect(10, start_y + 5, box_width, 24)
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


class FloatInputNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.ui_comp = TextBoxComponent("0.0", float)
        self.add_output(Pin("Value", PinType.FLOAT, ui_component=self.ui_comp))
        self._build_cached_surface()

    def evaluate(self, pin_name: str):
        return self.ui_comp.get_value()


class IntInputNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.ui_comp = TextBoxComponent("0", int)
        self.add_output(Pin("Value", PinType.INT, ui_component=self.ui_comp))
        self._build_cached_surface()

    def evaluate(self, pin_name: str):
        return self.ui_comp.get_value()


class BoolInputNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.ui_comp = BoolToggleComponent(False)
        self.add_output(Pin("Value", PinType.BOOL, ui_component=self.ui_comp))
        self._build_cached_surface()

    def evaluate(self, pin_name: str):
        return self.ui_comp.get_value()


class InstantiateNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_input(
            Pin("Identifier", PinType.STRING, ui_component=TextBoxComponent("cat", str))
        )
        self.add_output(Pin("Exec Right", PinType.EXEC))
        self.add_output(Pin("Object", PinType.GAMEOBJECT))
        self.instantiated_obj = None
        self._build_cached_surface()

    def execute(self, triggered_pin: Optional[Pin] = None):
        identifier = self.get_input_value("Identifier")
        if identifier:
            self.instantiated_obj = scene.Instantiate(str(identifier))
            add_console_log(f"Instantiated: {identifier}")
        else:
            add_console_log("Instantiate failed: No identifier")

        yield from self.trigger_out_pin("Exec Right")

    def evaluate(self, pin_name: str) -> Any:
        if pin_name == "Object":
            return self.instantiated_obj
        return super().evaluate(pin_name)

    def get_output_value(self, pin_name: str) -> Any:
        if pin_name == "Object":
            return self.instantiated_obj
        return super().get_output_value(pin_name)


class SetGameObjectPositionNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_input(Pin("Target", PinType.GAMEOBJECT))
        self.add_input(Pin("Position", PinType.VECTOR2))
        self.add_output(Pin("Exec Right", PinType.EXEC))
        self._build_cached_surface()

    def execute(self, triggered_pin: Optional[Pin] = None):
        target = self.get_input_value("Target")
        pos = self.get_input_value("Position")
        if target is not None and pos is not None:
            if isinstance(pos, pygame.Vector2):
                target.SetPosition(pos)
            else:
                target.SetPosition(pygame.Vector2(pos))
            add_console_log(f"Set position of {target.identifier}")
        else:
            add_console_log("SetGameObjectPosition failed: Missing Target or Position")

        yield from self.trigger_out_pin("Exec Right")


class GetGameObjectPositionNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(Pin("Target", PinType.GAMEOBJECT))
        self.add_output(Pin("Position", PinType.VECTOR2))
        self._build_cached_surface()

    def evaluate(self, pin_name: str):
        target = self.get_input_value("Target")
        if target is not None:
            return target.GetPosition()
        return pygame.Vector2(0, 0)


class DoForeverNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_output(Pin("Loop", PinType.EXEC))
        self._build_cached_surface()

    def execute(self, triggered_pin: Optional[Pin] = None):
        add_console_log(f"DoForeverNode initiated: {self.title}")
        while True:
            yield from self.trigger_out_pin("Loop")
            yield


class DoOnceNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_input(Pin("Reset", PinType.EXEC))
        self.add_output(Pin("Completed", PinType.EXEC))
        self.has_executed = False
        self._build_cached_surface()

    def execute(self, triggered_pin: Optional[Pin] = None):
        if triggered_pin and triggered_pin.name == "Reset":
            self.has_executed = False
            add_console_log(f"DoOnce Reset: {self.title}")
            return

        if not self.has_executed:
            self.has_executed = True
            add_console_log(f"DoOnce Executed: {self.title}")
            yield from self.trigger_out_pin("Completed")


class BranchNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_input(
            Pin("Condition", PinType.BOOL, ui_component=BoolToggleComponent(False))
        )
        self.add_output(Pin("True", PinType.EXEC))
        self.add_output(Pin("False", PinType.EXEC))
        self._build_cached_surface()

    def execute(self, triggered_pin: Optional[Pin] = None):
        condition = self.get_input_value("Condition")
        if condition:
            yield from self.trigger_out_pin("True")
        else:
            yield from self.trigger_out_pin("False")


class ForLoopNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_input(
            Pin("Start", PinType.INT, ui_component=TextBoxComponent("0", int))
        )
        self.add_input(Pin("End", PinType.INT, ui_component=TextBoxComponent("5", int)))

        self.add_output(Pin("Loop Body", PinType.EXEC))
        self.add_output(Pin("Index", PinType.INT))
        self.add_output(Pin("Completed", PinType.EXEC))

        self.current_index = 0
        self._build_cached_surface()

    def get_output_value(self, pin_name: str) -> Any:
        if pin_name == "Index":
            return self.current_index
        return super().get_output_value(pin_name)

    def execute(self, triggered_pin: Optional[Pin] = None):
        start_val = self.get_input_value("Start")
        end_val = self.get_input_value("End")

        start = int(start_val) if start_val is not None else 0
        end = int(end_val) if end_val is not None else 5
        step = 1 if start <= end else -1

        for i in range(start, end + step, step):
            self.current_index = i
            yield from self.trigger_out_pin("Loop Body")
            yield

        yield from self.trigger_out_pin("Completed")

    def evaluate(self, pin_name: str) -> Any:
        if pin_name == "Index":
            return self.current_index
        return super().evaluate(pin_name)


class SequenceNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_output(Pin("Then 0", PinType.EXEC))
        self.add_output(Pin("Then 1", PinType.EXEC))
        self.add_output(Pin("Then 2", PinType.EXEC))
        self._build_cached_surface()

    def execute(self, triggered_pin: Optional[Pin] = None):
        for pin in self.outputs:
            if pin.pin_type == PinType.EXEC and pin.name.startswith("Then"):
                yield from self.trigger_out_pin(pin.name)


class DelayNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_input(
            Pin("Seconds", PinType.FLOAT, ui_component=TextBoxComponent("1.0", float))
        )
        self.add_output(Pin("Exec Right", PinType.EXEC))
        self._build_cached_surface()

    def execute(self, triggered_pin: Optional[Pin] = None):
        add_console_log(f"DelayNode started: {self.title}")
        sec_val = self.get_input_value("Seconds")
        seconds = float(sec_val) if sec_val is not None and sec_val != "" else 1.0

        elapsed = 0.0
        while elapsed < seconds:
            dt = yield
            elapsed += dt or 0.0

        add_console_log(f"DelayNode complete: {self.title}")
        yield from self.trigger_out_pin("Exec Right")


class MoveToNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_input(Pin("From P1", PinType.VECTOR2))
        self.add_input(Pin("To P2", PinType.VECTOR2))
        self.add_input(
            Pin(
                "In Seconds", PinType.FLOAT, ui_component=TextBoxComponent("1.0", float)
            )
        )
        self.add_output(Pin("Exec Right", PinType.EXEC))
        self._build_cached_surface()

    def execute(self, triggered_pin: Optional[Pin] = None):
        add_console_log(f"MoveToNode started: {self.title}")
        p1_val = self.get_input_value("From P1")
        p2_val = self.get_input_value("To P2")
        sec_val = self.get_input_value("In Seconds")

        p1 = p1_val if isinstance(p1_val, pygame.Vector2) else pygame.Vector2(0, 0)
        p2 = p2_val if isinstance(p2_val, pygame.Vector2) else pygame.Vector2(400, 300)
        seconds = float(sec_val) if sec_val is not None and sec_val != "" else 1.0

        elapsed = 0.0
        global cat
        while elapsed < seconds:
            dt = yield
            elapsed += dt or 0.0
            t = min(elapsed / seconds, 1.0) if seconds > 0.0 else 1.0
            cat.SetPosition(p1.lerp(p2, t))

        add_console_log(f"MoveToNode complete: {self.title}")
        yield from self.trigger_out_pin("Exec Right")


class ChangeXByNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)

        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_input(
            Pin(
                "Change X By",
                PinType.FLOAT,
                ui_component=TextBoxComponent("100.0", float),
            )
        )
        self.add_input(
            Pin(
                "In Seconds", PinType.FLOAT, ui_component=TextBoxComponent("1.0", float)
            )
        )

        self.add_output(Pin("Exec Right", PinType.EXEC))
        self._build_cached_surface()

    def execute(self, triggered_pin: Optional[Pin] = None):
        add_console_log(f"ChangeXByNode started: {self.title}")
        change_val = self.get_input_value("Change X By")
        sec_val = self.get_input_value("In Seconds")

        delta_x = float(change_val) if change_val is not None else 100.0
        seconds = float(sec_val) if sec_val is not None else 1.0

        global cat
        start_pos = cat.GetPosition().copy()
        start_x = start_pos.x
        target_x = start_x + delta_x

        elapsed = 0.0
        while elapsed < seconds:
            dt = yield
            elapsed += dt or 0.0
            t = min(elapsed / seconds, 1.0) if seconds > 0 else 1.0
            new_x = start_x + (target_x - start_x) * t
            cat.SetPosition(pygame.Vector2(new_x, start_pos.y))

        cat.SetPosition(pygame.Vector2(target_x, start_pos.y))
        add_console_log(f"ChangeXByNode complete: {self.title}")
        yield from self.trigger_out_pin("Exec Right")


class ChangeYByNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)

        self.add_input(Pin("Exec Left", PinType.EXEC))
        self.add_input(
            Pin(
                "Change Y By",
                PinType.FLOAT,
                ui_component=TextBoxComponent("100.0", float),
            )
        )
        self.add_input(
            Pin(
                "In Seconds", PinType.FLOAT, ui_component=TextBoxComponent("1.0", float)
            )
        )

        self.add_output(Pin("Exec Right", PinType.EXEC))
        self._build_cached_surface()

    def execute(self, triggered_pin: Optional[Pin] = None):
        add_console_log(f"ChangeYByNode started: {self.title}")
        change_val = self.get_input_value("Change Y By")
        sec_val = self.get_input_value("In Seconds")

        delta_y = float(change_val) if change_val is not None else 100.0
        seconds = float(sec_val) if sec_val is not None else 1.0

        global cat
        start_pos = cat.GetPosition().copy()
        start_y = start_pos.y
        target_y = start_y + delta_y

        elapsed = 0.0
        while elapsed < seconds:
            dt = yield
            elapsed += dt or 0.0
            t = min(elapsed / seconds, 1.0) if seconds > 0 else 1.0
            new_y = start_y + (target_y - start_y) * t
            cat.SetPosition(pygame.Vector2(start_pos.x, new_y))

        cat.SetPosition(pygame.Vector2(start_pos.x, target_y))
        add_console_log(f"ChangeYByNode complete: {self.title}")
        yield from self.trigger_out_pin("Exec Right")


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


class NodePanel:
    def __init__(self, width: int):
        self.width = width
        self.scroll_y = 0
        self.node_prototypes = []
        self.total_height = 0

    def register_node(self, node_class, title, header_color):
        node = node_class(0, 0, title, header_color)
        self.node_prototypes.append(
            {"class": node_class, "title": title, "color": header_color, "node": node}
        )
        self.layout()

    def layout(self):
        y = 20
        for item in self.node_prototypes:
            node = item["node"]
            node.position = pygame.Vector2((self.width - node.width) // 2, y)
            node._build_cached_surface()
            y += node.bg_surface.get_height() + 20
        self.total_height = y

    def draw(self, screen: pygame.Surface):
        panel_rect = pygame.Rect(0, 0, self.width, screen.get_height())

        old_clip = screen.get_clip()
        screen.set_clip(panel_rect)

        pygame.draw.rect(screen, (30, 30, 30), panel_rect)

        for item in self.node_prototypes:
            node = item["node"]
            y_pos = node.position.y - self.scroll_y
            if -300 < y_pos < screen.get_height():
                screen.blit(node.bg_surface, (node.position.x, y_pos))

        pygame.draw.line(
            screen,
            (0, 0, 0),
            (self.width - 1, 0),
            (self.width - 1, screen.get_height()),
            2,
        )

        screen.set_clip(old_clip)


class ExecutionEngine:
    def __init__(self):
        self.active_tasks: List[types.GeneratorType] = []

    def start_chain(self, start_node: GraphNode):
        task_gen = start_node.execute()
        try:
            next(task_gen)
            self.active_tasks.append(task_gen)
        except StopIteration:
            pass

    def tick(self, dt: float):
        still_active = []
        for task in self.active_tasks:
            try:
                task.send(dt)
                still_active.append(task)
            except StopIteration:
                pass
        self.active_tasks = still_active

    def stop_all(self):
        self.active_tasks.clear()


class InputState:
    current_keys = None
    previous_keys = None
    current_mods = 0

    @classmethod
    def update(cls):
        cls.previous_keys = cls.current_keys
        cls.current_keys = pygame.key.get_pressed()
        cls.current_mods = pygame.key.get_mods()


class BaseKeyboardNode(GraphNode):
    def __init__(self, x: float, y: float, title: str, header_color: tuple) -> None:
        super().__init__(x, y, title, header_color)
        self.add_input(
            Pin("Key", PinType.STRING, ui_component=TextBoxComponent("space", str))
        )
        self.add_input(
            Pin("Ctrl", PinType.BOOL, ui_component=BoolToggleComponent(False))
        )
        self.add_input(
            Pin("Shift", PinType.BOOL, ui_component=BoolToggleComponent(False))
        )
        self.add_input(
            Pin("Alt", PinType.BOOL, ui_component=BoolToggleComponent(False))
        )
        self.add_output(Pin("Condition", PinType.BOOL))
        self._build_cached_surface()

    def get_key_state(self):
        key_name = self.get_input_value("Key")
        req_ctrl = self.get_input_value("Ctrl")
        req_shift = self.get_input_value("Shift")
        req_alt = self.get_input_value("Alt")

        if InputState.current_keys is None:
            return False, False, False

        try:
            # Convert string to pygame keycode ("space", "a", "right")
            k_code = pygame.key.key_code(str(key_name).strip().lower())
        except (ValueError, NotImplementedError):
            return False, False, False

        mods = InputState.current_mods
        if req_ctrl and not (mods & pygame.KMOD_CTRL):
            return False, False, False
        if req_shift and not (mods & pygame.KMOD_SHIFT):
            return False, False, False
        if req_alt and not (mods & pygame.KMOD_ALT):
            return False, False, False

        is_down = bool(InputState.current_keys[k_code])
        was_down = (
            bool(InputState.previous_keys[k_code])
            if InputState.previous_keys
            else False
        )

        return True, is_down, was_down


class KeyPressedNode(BaseKeyboardNode):
    def evaluate(self, pin_name: str):
        valid, is_down, was_down = self.get_key_state()
        return valid and is_down


class KeyPressedJustNowNode(BaseKeyboardNode):
    def evaluate(self, pin_name: str):
        valid, is_down, was_down = self.get_key_state()
        return valid and is_down and not was_down


class KeyReleasedNode(BaseKeyboardNode):
    def evaluate(self, pin_name: str):
        valid, is_down, was_down = self.get_key_state()
        return valid and not is_down


class KeyReleasedJustNowNode(BaseKeyboardNode):
    def evaluate(self, pin_name: str):
        valid, is_down, was_down = self.get_key_state()
        return valid and not is_down and was_down


def main():
    global WIDTH, HEIGHT, CAM_POS

    CAM_POS.update(WIDTH // 2, HEIGHT // 2)

    panning = False
    last_mouse_pos = pygame.mouse.get_pos()

    cat_sprite = pygame.image.load("cat.png").convert_alpha()

    node_panel = NodePanel(240)

    node_panel.register_node(KeyPressedNode, "Key Pressed", (180, 100, 100))
    node_panel.register_node(
        KeyPressedJustNowNode, "Key Pressed Just Now", (180, 80, 80)
    )
    node_panel.register_node(KeyReleasedNode, "Key Released", (180, 100, 100))
    node_panel.register_node(
        KeyReleasedJustNowNode, "Key Released Just Now", (180, 80, 80)
    )

    node_panel.register_node(PrintNode, "Print Hello World", (50, 200, 50))
    node_panel.register_node(StringConstantNode, "String Constant", (50, 50, 200))
    node_panel.register_node(TextInputNode, "Text Input", (150, 50, 150))

    node_panel.register_node(SetPositionNode, "Set Cat Position", (200, 200, 50))

    node_panel.register_node(InstantiateNode, "Instantiate Object", (250, 100, 50))
    node_panel.register_node(
        SetGameObjectPositionNode, "Set Obj Position", (200, 150, 50)
    )
    node_panel.register_node(
        GetGameObjectPositionNode, "Get Obj Position", (150, 150, 50)
    )

    node_panel.register_node(FloatInputNode, "Float Input", (150, 150, 150))
    node_panel.register_node(IntInputNode, "Int Input", (140, 140, 140))
    node_panel.register_node(MakeVector2Node, "Make Vector2 Node", (200, 50, 50))
    node_panel.register_node(DelayNode, "Delay Node", (100, 100, 100))
    node_panel.register_node(MoveToNode, "Move Cat", (120, 80, 180))
    node_panel.register_node(ChangeXByNode, "Change X By", (120, 80, 180))
    node_panel.register_node(ChangeYByNode, "Change Y By", (120, 80, 180))
    node_panel.register_node(DoForeverNode, "Do Forever", (110, 110, 110))
    node_panel.register_node(DoOnceNode, "Do Once", (160, 80, 80))
    node_panel.register_node(BranchNode, "Branch (If/Else)", (160, 100, 50))
    node_panel.register_node(BoolInputNode, "Bool Condition", (100, 100, 100))
    node_panel.register_node(ForLoopNode, "For Loop", (80, 120, 160))
    node_panel.register_node(SequenceNode, "Sequence", (100, 150, 100))

    begin_play_node = GraphNode(300, 100, "Event BeginPlay", (200, 50, 50))
    begin_play_exec_right_pin = Pin("Exec Right", PinType.EXEC)
    begin_play_node.add_output(begin_play_exec_right_pin)
    begin_play_node._build_cached_surface()

    clicked_pin: Optional[Pin] = None

    def on_pin_clicked(pin: Pin) -> None:
        nonlocal clicked_pin
        clicked_pin = pin
        node_name = pin.node.title if pin.node else "Unknown Node"
        print(f"Pin clicked: {pin.name} on {node_name}")

    begin_play_exec_right_pin.on_clicked = on_pin_clicked

    graph: list[GraphNode] = [
        begin_play_node,
    ]

    dragging_node: Optional[GraphNode] = None
    selected_node: Optional[GraphNode] = None
    drag_offset = pygame.Vector2()

    vm_engine = ExecutionEngine()

    clock = pygame.time.Clock()
    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        current_mouse_pos = pygame.mouse.get_pos()
        if panning:
            CAM_POS += pygame.Vector2(current_mouse_pos) - pygame.Vector2(
                last_mouse_pos
            )

        InputState.update()

        last_mouse_pos = current_mouse_pos
        world_mouse = screen_to_world(pygame.Vector2(current_mouse_pos))

        vm_engine.tick(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 2:  # Middle mouse button
                    panning = True
                elif event.button == 1:  # Left mouse button
                    if current_mouse_pos[0] < node_panel.width:
                        # Handle panel click - Spawning new node
                        for item in node_panel.node_prototypes:
                            node = item["node"]
                            node_rect = pygame.Rect(
                                node.position.x,
                                node.position.y - node_panel.scroll_y,
                                node.width,
                                node.bg_surface.get_height(),
                            )
                            if node_rect.collidepoint(current_mouse_pos):
                                world_pos = screen_to_world(
                                    pygame.Vector2(current_mouse_pos)
                                )
                                new_node = item["class"](
                                    world_pos.x - node.width / 2,
                                    world_pos.y - HEADER_HEIGHT / 2,
                                    item["title"],
                                    item["color"],
                                )
                                for pin in (*new_node.inputs, *new_node.outputs):
                                    pin.on_clicked = on_pin_clicked
                                graph.append(new_node)

                                dragging_node = new_node
                                selected_node = new_node
                                drag_offset = world_pos - new_node.pos()
                                break
                    else:
                        # Handle workspace click
                        node_clicked = False
                        for node in reversed(
                            graph
                        ):  # Check nodes in reverse order for proper z-index
                            if node.handle_mouse(event, world_mouse):
                                dragging_node = node
                                selected_node = node
                                drag_offset = world_mouse - dragging_node.pos()
                                node_clicked = True
                                break
                        if not node_clicked:
                            selected_node = None
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
                        if current_mouse_pos[0] >= node_panel.width:
                            for node in graph:
                                for pin in (*node.inputs, *node.outputs):
                                    pin_pos = node.get_pin_world_pos(pin)
                                    screen_pin_pos = world_to_screen(pin_pos)

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
            elif event.type == pygame.MOUSEWHEEL:
                if current_mouse_pos[0] < node_panel.width:
                    max_scroll = max(0, node_panel.total_height - HEIGHT)
                    node_panel.scroll_y -= event.y * 20
                    node_panel.scroll_y = max(0, min(node_panel.scroll_y, max_scroll))
            elif event.type == pygame.VIDEORESIZE:
                print(f"Window resized to: {event.w}x{event.h}")
                WIDTH, HEIGHT = screen.get_size()
                max_scroll = max(0, node_panel.total_height - HEIGHT)
                node_panel.scroll_y = max(0, min(node_panel.scroll_y, max_scroll))
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c and (
                    pygame.key.get_mods() & pygame.KMOD_CTRL
                ):
                    if selected_node and not selected_node.is_editing_ui():
                        cls = selected_node.__class__
                        new_pos = selected_node.pos() + pygame.Vector2(30, 30)

                        new_node = cls(
                            new_pos.x,
                            new_pos.y,
                            selected_node.title,
                            selected_node.header_color,
                        )

                        # Clear default pins added during constructor to avoid duplicates.
                        new_node.inputs.clear()
                        new_node.outputs.clear()

                        # Create and set up exact copies of the inputs and outputs.
                        for pin in selected_node.inputs:
                            ui_comp_copy = None
                            if pin.ui_component:
                                if isinstance(pin.ui_component, TextBoxComponent):
                                    ui_comp_copy = TextBoxComponent(
                                        pin.ui_component.text,
                                        pin.ui_component.cast_type,
                                    )
                                elif isinstance(pin.ui_component, BoolToggleComponent):
                                    ui_comp_copy = BoolToggleComponent(
                                        pin.ui_component.value
                                    )

                            new_pin = Pin(
                                pin.name, pin.pin_type, ui_component=ui_comp_copy
                            )
                            new_pin.on_clicked = on_pin_clicked
                            new_node.add_input(new_pin)

                        for pin in selected_node.outputs:
                            ui_comp_copy = None
                            if pin.ui_component:
                                if isinstance(pin.ui_component, TextBoxComponent):
                                    ui_comp_copy = TextBoxComponent(
                                        pin.ui_component.text,
                                        pin.ui_component.cast_type,
                                    )
                                elif isinstance(pin.ui_component, BoolToggleComponent):
                                    ui_comp_copy = BoolToggleComponent(
                                        pin.ui_component.value
                                    )

                            new_pin = Pin(
                                pin.name, pin.pin_type, ui_component=ui_comp_copy
                            )
                            new_pin.on_clicked = on_pin_clicked
                            new_node.add_output(new_pin)

                        new_node._build_cached_surface()
                        graph.append(new_node)
                        selected_node = new_node
                        print(f"Copied node: {new_node.title}")

            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]:
                if clicked_pin:
                    clicked_pin = None
                    print("Wire drawing canceled.")
            elif keys[pygame.K_KP_ENTER] or keys[pygame.K_RETURN]:
                print("Executing test VM...")

                vm_engine.stop_all()  # Clear previous tasks if any.
                vm_engine.start_chain(begin_play_node)

            is_in_panel = current_mouse_pos[0] < node_panel.width

            for node in graph:
                if is_in_panel and event.type in (
                    pygame.MOUSEBUTTONDOWN,
                    pygame.MOUSEBUTTONUP,
                ):
                    continue

                # If mouse is hovering over the panel, pass an extremely far-away coordinate
                # so workspace pins correctly un-hover.
                if (
                    is_in_panel
                    and event.type == pygame.MOUSEMOTION
                    and not dragging_node
                ):
                    node.handle_events(
                        event, screen_to_world(pygame.Vector2(-99999, -99999))
                    )
                else:
                    node.handle_events(event, world_mouse)

        screen.fill(BG_COLOR)

        draw_grid(screen, WIDTH, HEIGHT)

        cat.RenderAt(surface=screen, pos=world_to_screen(cat.GetPosition()))

        # Render all newly added objects in the scene so instantiated objects show up.
        for obj in scene.nodes:
            if obj is not cat and hasattr(obj, "RenderAt"):
                obj.RenderAt(surface=screen, pos=world_to_screen(obj.GetPosition()))

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

        clear_expired_logs()

        log_pos = pygame.Vector2(node_panel.width + 20, 20)
        for i, console_log in enumerate(console_logs):
            text_surf = TITLE_FONT.render(console_log.log, True, (220, 200, 10))
            screen.blit(text_surf, log_pos + pygame.Vector2(0, i * 20))

        node_panel.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
