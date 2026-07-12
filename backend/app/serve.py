"""Run the Myomatlas API server.

Reload is off by default and has to be asked for. The reloader watches the source tree
and restarts the process when a file changes, and the pipeline writes its caches under
data/, so with a wide watch path the server can restart itself mid-request and look like
it shut down on its own.

Usage:
    python -m app.serve                  # normal, no reload
    python -m app.serve --reload         # while editing backend code
"""

from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Myomatlas API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Development only. Watches app/ and restarts on code changes.",
    )
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        # Watch only the source, never data/, so writing a cache cannot trigger a restart.
        reload_dirs=["app"] if args.reload else None,
    )


if __name__ == "__main__":
    main()
