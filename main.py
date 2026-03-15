#!/usr/bin/env python3
"""Legacy push entrypoint kept for compatibility during architecture migration."""
import sys

from src.app.jobs.push_job import run_push_job



def main():
    """Keep the old entrypoint, but route execution through the new jobs layer."""
    return run_push_job()


if __name__ == "__main__":
    sys.exit(main())
