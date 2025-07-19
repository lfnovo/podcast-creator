"""
Async helpers for running async functions in Streamlit.

Provides utilities to handle async operations in Streamlit apps.
"""

import asyncio
import threading
from typing import Any, Callable, Coroutine, Optional
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
import time


def run_async_in_streamlit(async_func: Callable[..., Coroutine], *args, **kwargs) -> Any:
    """
    Run an async function in Streamlit.
    
    Args:
        async_func: Async function to run
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Result of the async function
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an event loop, we need to run in a new thread
            with ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, async_func(*args, **kwargs))
                return future.result()
        else:
            # If no event loop is running, we can run directly
            return loop.run_until_complete(async_func(*args, **kwargs))
    except RuntimeError:
        # No event loop exists, create a new one
        return asyncio.run(async_func(*args, **kwargs))


class AsyncTaskManager:
    """Manager for handling async tasks with progress tracking."""
    
    def __init__(self):
        self.tasks = {}
        self.results = {}
        self.errors = {}
        self.progress = {}
    
    def run_task(self, task_id: str, async_func: Callable, *args, **kwargs) -> None:
        """
        Run an async task with progress tracking.
        
        Args:
            task_id: Unique identifier for the task
            async_func: Async function to run
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
        """
        def run_in_thread():
            try:
                self.progress[task_id] = {"status": "running", "progress": 0}
                result = asyncio.run(async_func(*args, **kwargs))
                self.results[task_id] = result
                self.progress[task_id] = {"status": "completed", "progress": 100}
            except Exception as e:
                self.errors[task_id] = str(e)
                self.progress[task_id] = {"status": "error", "progress": 0}
        
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        self.tasks[task_id] = thread
    
    def get_task_status(self, task_id: str) -> dict:
        """Get the status of a task."""
        return self.progress.get(task_id, {"status": "not_found", "progress": 0})
    
    def get_task_result(self, task_id: str) -> Any:
        """Get the result of a completed task."""
        return self.results.get(task_id)
    
    def get_task_error(self, task_id: str) -> Optional[str]:
        """Get the error from a failed task."""
        return self.errors.get(task_id)
    
    def is_task_running(self, task_id: str) -> bool:
        """Check if a task is currently running."""
        return task_id in self.tasks and self.tasks[task_id].is_alive()
    
    def is_task_completed(self, task_id: str) -> bool:
        """Check if a task has completed successfully."""
        return task_id in self.results
    
    def is_task_failed(self, task_id: str) -> bool:
        """Check if a task has failed."""
        return task_id in self.errors
    
    def cleanup_task(self, task_id: str) -> None:
        """Clean up task data."""
        if task_id in self.tasks:
            del self.tasks[task_id]
        if task_id in self.results:
            del self.results[task_id]
        if task_id in self.errors:
            del self.errors[task_id]
        if task_id in self.progress:
            del self.progress[task_id]


class StreamlitAsyncContext:
    """Context manager for async operations in Streamlit."""
    
    def __init__(self, progress_bar: bool = True, status_text: bool = True):
        self.progress_bar = progress_bar
        self.status_text = status_text
        self.progress_bar_obj = None
        self.status_text_obj = None
    
    def __enter__(self):
        if self.progress_bar:
            self.progress_bar_obj = st.progress(0)
        if self.status_text:
            self.status_text_obj = st.empty()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress_bar_obj:
            self.progress_bar_obj.empty()
        if self.status_text_obj:
            self.status_text_obj.empty()
    
    def update_progress(self, progress: float, status: str = ""):
        """Update the progress bar and status text."""
        if self.progress_bar_obj:
            self.progress_bar_obj.progress(progress)
        if self.status_text_obj and status:
            self.status_text_obj.text(status)


def create_async_task_with_progress(
    async_func: Callable, 
    progress_callback: Optional[Callable] = None,
    *args, 
    **kwargs
) -> Callable:
    """
    Create an async task wrapper that supports progress reporting.
    
    Args:
        async_func: The async function to wrap
        progress_callback: Optional callback for progress updates
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Wrapped function that can be executed
    """
    async def wrapper():
        if progress_callback:
            progress_callback(0, "Starting task...")
        
        try:
            result = await async_func(*args, **kwargs)
            if progress_callback:
                progress_callback(100, "Task completed!")
            return result
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Task failed: {str(e)}")
            raise
    
    return wrapper


def run_async_with_progress(
    async_func: Callable,
    progress_container,
    status_container,
    *args,
    **kwargs
) -> Any:
    """
    Run an async function with progress display in Streamlit.
    
    Args:
        async_func: Async function to run
        progress_container: Streamlit container for progress bar
        status_container: Streamlit container for status text
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Result of the async function
    """
    progress_bar = progress_container.progress(0)
    status_text = status_container.empty()
    
    def update_progress(progress: float, status: str = ""):
        progress_bar.progress(progress)
        if status:
            status_text.text(status)
    
    try:
        # Create wrapper with progress callback
        async def wrapper():
            update_progress(0, "Starting...")
            try:
                result = await async_func(*args, **kwargs)
                update_progress(100, "Completed!")
                return result
            except Exception as e:
                update_progress(0, f"Failed: {str(e)}")
                raise
        
        # Run the async function
        result = run_async_in_streamlit(wrapper)
        
        # Clean up progress indicators
        time.sleep(1)  # Give user time to see completion
        progress_bar.empty()
        status_text.empty()
        
        return result
        
    except Exception:
        # Clean up progress indicators on error
        progress_bar.empty()
        status_text.empty()
        raise


def handle_async_errors(async_func: Callable) -> Callable:
    """
    Decorator to handle async errors in Streamlit.
    
    Args:
        async_func: Async function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    async def wrapper(*args, **kwargs):
        try:
            return await async_func(*args, **kwargs)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Please check your configuration and try again.")
            raise
    
    return wrapper


# Global task manager instance
_task_manager = AsyncTaskManager()


def get_task_manager() -> AsyncTaskManager:
    """Get the global task manager instance."""
    return _task_manager


def run_background_task(task_id: str, async_func: Callable, *args, **kwargs) -> None:
    """
    Run an async task in the background.
    
    Args:
        task_id: Unique identifier for the task
        async_func: Async function to run
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    """
    _task_manager.run_task(task_id, async_func, *args, **kwargs)


def get_background_task_status(task_id: str) -> dict:
    """Get the status of a background task."""
    return _task_manager.get_task_status(task_id)


def get_background_task_result(task_id: str) -> Any:
    """Get the result of a completed background task."""
    return _task_manager.get_task_result(task_id)


def cleanup_background_task(task_id: str) -> None:
    """Clean up a background task."""
    _task_manager.cleanup_task(task_id)