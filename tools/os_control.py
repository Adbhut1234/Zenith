import logging
import asyncio
import pyautogui
from computer_use import computer_use_loop
from livekit.agents import function_tool, RunContext
import ui_state

@function_tool()
async def move_and_click_mouse(
    context: RunContext,  # type: ignore
    x: int,
    y: int,
    click: bool = True
) -> str:
    """
    Move the mouse to a known (x, y) coordinate and optionally click.
    ONLY use this when exact coordinates are explicitly given (e.g. the user
    says "click at 500, 300", or you just ran control_computer and it reported
    the coordinate). Do NOT use this to click something you haven't confirmed
    the location of — use control_computer for that instead.
    """
    try:
        logging.info(f"Moving mouse to ({x}, {y})")
        await asyncio.to_thread(pyautogui.moveTo, x, y, duration=0.5)
        if click:
            await asyncio.to_thread(pyautogui.click)
            return f"Successfully moved to ({x}, {y}) and clicked."
        return f"Successfully moved to ({x}, {y})."
    except Exception as e:
        return f"Failed to control mouse: {str(e)}"

@function_tool()
async def type_keyboard_text(
    context: RunContext,  # type: ignore
    text: str,
    press_enter: bool = True
) -> str:
    """
    Type text wherever the cursor is currently focused. Use this for quick
    follow-up text entry right after a click you already made (e.g. via
    control_computer), not as the primary way to fill out a form from scratch
    — for that, use control_computer so each field can be visually verified.
    """
    try:
        logging.info(f"Typing text: {text}")
        await asyncio.to_thread(pyautogui.write, text, interval=0.05)
        if press_enter:
            await asyncio.to_thread(pyautogui.press, 'enter')
            return f"Successfully typed text and pressed Enter."
        return f"Successfully typed text."
    except Exception as e:
        return f"Failed to type on keyboard: {str(e)}"

@function_tool()
async def press_keyboard_shortcut(
    context: RunContext,  # type: ignore
    keys: str
) -> str:
    """
    Press a keyboard shortcut (e.g. 'ctrl,c', 'win,d', 'alt,tab', 'enter', 'esc').
    Separate multiple keys with commas if they should be pressed simultaneously.
    """
    try:
        logging.info(f"Pressing shortcut: {keys}")
        key_list = [k.strip() for k in keys.split(',')]
        await asyncio.to_thread(pyautogui.hotkey, *key_list)
        return f"Successfully pressed {keys}."
    except Exception as e:
        return f"Failed to press shortcut: {str(e)}"

@function_tool()
async def control_computer(context: RunContext, task: str) -> str:
    """
    Take control of the screen to complete a multi-step visual task — looking at screenshots,
    clicking, typing, and verifying each step before moving on. Use this instead of
    move_and_click_mouse/type_keyboard_text when the task needs precise visual grounding
    (e.g. "open Spotify and play my workout playlist", "fill out this form").
    """
    try:
        ui_state.set_text(f"👁️ Controlling screen for '{task}'...")
        return await computer_use_loop(task)
    except Exception as e:
        logging.error(f"control_computer failed: {e}")
        return f"Computer control task failed: {str(e)}"
