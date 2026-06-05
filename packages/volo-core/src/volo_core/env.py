"""Optional ``.env`` loading for entrypoints (bible §11 twelve-factor config).

Entrypoints (the CLI, the API) call :func:`load_env` once at startup so a local ``.env`` file
is picked up automatically — no need to export every variable by hand. Explicitly-exported
environment variables always win (``override=False``), and the call is a safe no-op if
``python-dotenv`` isn't installed.
"""

from __future__ import annotations

_loaded = False


def load_env() -> None:
    """Load a ``.env`` file (searching CWD upward) into ``os.environ`` — idempotent."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:  # pragma: no cover - dotenv is an entrypoint dep, optional for core
        return
    load_dotenv(find_dotenv(usecwd=True), override=False)
