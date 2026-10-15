from collections.abc import Callable
from datetime import datetime

# Job registry: name -> function
_jobs: dict[str, Callable[[datetime], dict]] = {}


def register(name: str):
    """Decorator to register a job function.

    Args:
        name: The unique name of the job
    """

    def decorator(fn: Callable[[datetime], dict]) -> Callable[[datetime], dict]:
        _jobs[name] = fn
        return fn

    return decorator


def get_job(name: str) -> Callable[[datetime], dict] | None:
    """Get a registered job by name.

    Args:
        name: The job name

    Returns:
        The job function, or None if not found
    """
    return _jobs.get(name)


def list_jobs() -> list[str]:
    """List all registered job names.

    Returns:
        List of job names
    """
    return list(_jobs.keys())
