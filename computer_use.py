import logging
from uia_control import uia_loop, UIANotSupportedError

async def computer_use_loop(task: str, max_steps: int = 15) -> str:
    """
    Delegates to the text-based UIA control loop.
    Vision models and screenshot fallbacks have been entirely removed.
    """
    try:
        logging.info("Attempting task via UIA (no screenshot needed)")
        return await uia_loop(task, max_steps=max_steps)
    except UIANotSupportedError:
        return "UIA not supported for this app. Vision fallback has been removed."
    except Exception as e:
        logging.warning(f"UIA loop failed ({e})")
        return f"Computer control task failed: {str(e)}"
