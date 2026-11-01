"""
Background Worker Swarm Manager for Zenith AI
Orchestrates asynchronous, non-blocking background workers for long-running
operations (autonomous web tasks, deep research, computer use, disk ops).
Keeps real-time voice streaming completely free and responsive while tasks execute in parallel.
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable, Any
from livekit.agents import function_tool, RunContext
import ui_state

logger = logging.getLogger("zenith.task_manager")


@dataclass
class BackgroundTask:
    task_id: str
    task_type: str
    description: str
    status: str  # "running" | "completed" | "failed" | "cancelled"
    start_time: float
    end_time: Optional[float] = None
    progress: str = "Initiated"
    result: Optional[str] = None
    error: Optional[str] = None
    task_ref: Optional[asyncio.Task] = field(default=None, repr=False)

    @property
    def duration_seconds(self) -> float:
        end = self.end_time if self.end_time else time.time()
        return round(end - self.start_time, 1)


class TaskManager:
    """Central registry and lifecycle manager for Zenith's background worker swarm."""
    def __init__(self):
        self._tasks: Dict[str, BackgroundTask] = {}
        self._counter: int = 0
        self._notifier_callback: Optional[Callable[[str], Any]] = None

    def set_notifier(self, callback: Callable[[str], Any]) -> None:
        """Sets the voice notification callback (e.g. session.say) called on task completion."""
        self._notifier_callback = callback

    def create_task_id(self, task_type: str) -> str:
        self._counter += 1
        prefix = task_type.replace("_", "-")[:8]
        return f"task-{prefix}-{self._counter}"

    def spawn(
        self,
        task_type: str,
        description: str,
        coro_fn: Callable[..., Any],
        *args,
        **kwargs
    ) -> BackgroundTask:
        """Spawns an asynchronous background worker and tracks it in the swarm registry."""
        task_id = self.create_task_id(task_type)
        bg_task = BackgroundTask(
            task_id=task_id,
            task_type=task_type,
            description=description,
            status="running",
            start_time=time.time(),
            progress="Worker started in background"
        )

        async def _runner():
            try:
                logger.info(f"Background worker [{task_id}] '{description}' started.")
                ui_state.set_text(f"⚙️ {task_type[:12]} | {description[:20]}")
                bg_task.progress = "Executing task logic..."

                res = await coro_fn(*args, **kwargs)

                bg_task.status = "completed"
                bg_task.end_time = time.time()
                bg_task.result = str(res)
                bg_task.progress = "Completed successfully"
                logger.info(f"Background worker [{task_id}] completed in {bg_task.duration_seconds}s.")
                ui_state.set_text(f"✅ Finished: {description[:20]}")

                # Trigger proactive vocal notification if registered
                if self._notifier_callback:
                    brief = bg_task.result[:180] if bg_task.result else "Task completed."
                    announcement = f"Sir, the background task for '{description}' has completed. Here is the summary: {brief}"
                    try:
                        res_coro = self._notifier_callback(announcement)
                        if asyncio.iscoroutine(res_coro):
                            await res_coro
                    except Exception as notify_err:
                        logger.error(f"Failed to announce background task completion: {notify_err}")

            except asyncio.CancelledError:
                bg_task.status = "cancelled"
                bg_task.end_time = time.time()
                bg_task.progress = "Cancelled by user or system"
                logger.info(f"Background worker [{task_id}] cancelled.")
                ui_state.set_text(f"⏹️ Cancelled: {description[:20]}")
                raise
            except Exception as e:
                bg_task.status = "failed"
                bg_task.end_time = time.time()
                bg_task.error = str(e)
                bg_task.progress = f"Failed with error: {e}"
                logger.error(f"Background worker [{task_id}] failed: {e}")
                ui_state.set_text(f"⚠️ Failed: {description[:20]}")
                if self._notifier_callback:
                    try:
                        res_coro = self._notifier_callback(f"Sir, the background task '{description}' encountered an error: {e}")
                        if asyncio.iscoroutine(res_coro):
                            await res_coro
                    except Exception:
                        pass

        async_task = asyncio.create_task(_runner(), name=f"zenith-bg-{task_id}")
        bg_task.task_ref = async_task
        self._tasks[task_id] = bg_task
        return bg_task

    def cancel(self, task_id: str) -> bool:
        """Cancels a specific background worker by ID."""
        task = self._tasks.get(task_id)
        if task and task.status == "running" and task.task_ref and not task.task_ref.done():
            task.task_ref.cancel()
            task.status = "cancelled"
            return True
        return False

    def cancel_all(self) -> int:
        """Cancels all active background workers."""
        cancelled_count = 0
        for task in self._tasks.values():
            if task.status == "running" and task.task_ref and not task.task_ref.done():
                task.task_ref.cancel()
                task.status = "cancelled"
                cancelled_count += 1
        return cancelled_count

    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        return self._tasks.get(task_id)

    def list_active_tasks(self) -> List[BackgroundTask]:
        return [t for t in self._tasks.values() if t.status == "running"]

    def list_all_tasks(self) -> List[BackgroundTask]:
        return list(self._tasks.values())


# Global TaskManager singleton instance
task_manager = TaskManager()


# --- Function Tools Exposed to Gemini Realtime ---

@function_tool()
async def dispatch_background_task(
    context: RunContext,  # type: ignore
    task_type: str,
    details: str
) -> str:
    """
    Dispatch a long-running, heavy, or multi-step operation to Zenith's background worker swarm.
    The task executes asynchronously in parallel, keeping the voice audio channel completely free
    and non-blocking so the user and Zenith can continue speaking naturally.
    
    Supported task_type values:
    - 'web_task': Multi-step autonomous web browsing, product hunting, scraping, or form filling.
    - 'research': Deep AI multi-source research dossier compilation on a topic.
    - 'academic_search': ArXiv academic and scientific preprint literature search.
    - 'computer_task': Multi-step visual desktop computer automation.
    - 'disk_cleanup': Background temporary files and junk cleanup.
    
    Args:
        task_type: The category of worker ('web_task' | 'research' | 'academic_search' | 'computer_task' | 'disk_cleanup').
        details: Specific instruction or search topic for the worker.
    """
    clean_type = task_type.strip().lower()
    
    if clean_type in ["web_task", "web", "browser", "browse"]:
        from agent_tools.web import autonomous_web_task
        func = getattr(autonomous_web_task, "__wrapped__", getattr(autonomous_web_task, "_func", autonomous_web_task))
        task = task_manager.spawn("web_task", details, func, context=None, task=details, max_steps=8)

    elif clean_type in ["research", "deep_research"]:
        from agent_tools.research import deep_research
        func = getattr(deep_research, "__wrapped__", getattr(deep_research, "_func", deep_research))
        task = task_manager.spawn("research", details, func, context=None, topic=details, save_report=True)

    elif clean_type in ["academic_search", "arxiv", "paper"]:
        from agent_tools.research import search_academic_papers
        func = getattr(search_academic_papers, "__wrapped__", getattr(search_academic_papers, "_func", search_academic_papers))
        task = task_manager.spawn("academic_search", details, func, context=None, query=details, max_results=5)

    elif clean_type in ["computer_task", "computer_use", "screen"]:
        from computer_use import computer_use_loop
        task = task_manager.spawn("computer_task", details, computer_use_loop, task=details, max_steps=10)

    elif clean_type in ["disk_cleanup", "clean_disk"]:
        from agent_tools.system import clean_disk_temp_junk
        func = getattr(clean_disk_temp_junk, "__wrapped__", getattr(clean_disk_temp_junk, "_func", clean_disk_temp_junk))
        task = task_manager.spawn("disk_cleanup", "Clean disk temp files", func, context=None)

    else:
        return f"Unknown task_type '{task_type}'. Available: 'web_task', 'research', 'academic_search', 'computer_task', 'disk_cleanup'."

    return (
        f"Background worker successfully dispatched with ID: {task.task_id}.\n"
        f"Voice channel is completely open. Inform Sir that '{details}' is being processed in the background, "
        f"and you will notify him the moment it finishes."
    )


@function_tool()
async def check_background_tasks(
    context: RunContext,  # type: ignore
    task_id: Optional[str] = None
) -> str:
    """
    Check the current live execution status, progress, or results of background worker swarm tasks.
    Use this when the user asks "what's running in the background?", "is my research done?",
    or asks for the status/result of a background task.
    """
    if task_id:
        t = task_manager.get_task(task_id.strip())
        if not t:
            return f"No background task found with ID '{task_id}'."
        res_snippet = f" | Result: {t.result[:200]}" if t.result else ""
        err_snippet = f" | Error: {t.error}" if t.error else ""
        return f"Task [{t.task_id}] ({t.task_type}): Status={t.status.upper()} | Duration={t.duration_seconds}s | Progress: {t.progress}{res_snippet}{err_snippet}"

    all_tasks = task_manager.list_all_tasks()
    if not all_tasks:
        return "No background tasks have been dispatched in this session."

    lines = ["Current Background Worker Swarm Status:"]
    for t in all_tasks[-5:]:
        status_icon = "🟢 RUNNING" if t.status == "running" else ("✅ DONE" if t.status == "completed" else "⏹️ " + t.status.upper())
        lines.append(f"- [{t.task_id}] {status_icon} | {t.task_type}: '{t.description[:35]}' ({t.duration_seconds}s) - {t.progress}")

    return "\n".join(lines)


@function_tool()
async def cancel_background_task(
    context: RunContext,  # type: ignore
    task_id: Optional[str] = None
) -> str:
    """
    Cancel an ongoing background worker task, or cancel all active background tasks.
    Use this when the user says "cancel the background task", "stop the research", or "abort background jobs".
    """
    if task_id and task_id.lower() not in ["all", "everything"]:
        cancelled = task_manager.cancel(task_id.strip())
        if cancelled:
            return f"Background task '{task_id}' has been cancelled."
        return f"Could not cancel task '{task_id}' (it may already be completed or not exist)."

    count = task_manager.cancel_all()
    return f"Successfully aborted {count} active background worker task(s)."
