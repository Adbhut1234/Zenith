from .web import get_weather, search_web, send_email, open_website
from .system import execute_pc_command, write_and_open_file, open_application, get_now_playing
from .os_control import move_and_click_mouse, type_keyboard_text, press_keyboard_shortcut, control_computer

__all__ = [
    "get_weather", "search_web", "send_email", "open_website",
    "execute_pc_command", "write_and_open_file", "open_application", "get_now_playing",
    "move_and_click_mouse", "type_keyboard_text", "press_keyboard_shortcut", "control_computer"
]
