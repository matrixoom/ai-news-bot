"""Scheduled job entrypoints."""


def run_push_job():
    """Lazy import to keep the package importable before optional deps are installed."""
    from .push_job import run_push_job as _run_push_job

    return _run_push_job()


__all__ = ["run_push_job"]
