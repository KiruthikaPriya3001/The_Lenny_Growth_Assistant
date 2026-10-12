#!/usr/bin/env python3
"""
Lenny Growth Assistant — startup helper script.

Usage:
  python start.py            # start backend only
  python start.py --frontend # start backend + frontend dev server

This script:
  1. Checks Python/Node versions
  2. Verifies .env exists
  3. Checks PostgreSQL connection
  4. Runs database migrations (alembic upgrade head)
  5. Starts the FastAPI backend
  6. Optionally starts the Vite frontend dev server in a subprocess

Run from the project root directory.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def banner():
    print("\n" + "═" * 56)
    print("  🌱 Lenny Growth Assistant — powered by GrowthOS")
    print("═" * 56 + "\n")


def check(condition: bool, msg: str, fatal: bool = False):
    if condition:
        print(f"  ✓  {msg}")
    else:
        print(f"  {'✗' if fatal else '!'} {msg}")
        if fatal:
            sys.exit(1)


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def run_migration():
    print("\n▸ Running database migrations…")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  ✗ Migration failed:\n{result.stderr}")
        print("  Trying to continue anyway (tables may already exist)…")
    else:
        print("  ✓ Migrations applied.")


def start_backend():
    if port_in_use(8000):
        print("\n▸ Backend already running on http://localhost:8000")
        print("  Reusing the active server instead of launching a duplicate instance.\n")
        return None
    print("\n▸ Starting FastAPI backend on http://localhost:8000")
    print("  API docs:  http://localhost:8000/api/docs")
    print("  Press Ctrl+C to stop.\n")
    return subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
        ],
        cwd=BACKEND,
    )


def start_frontend():
    if port_in_use(5173):
        print("▸ Frontend already running on http://localhost:5173")
        return None
    print("▸ Starting frontend dev server on http://localhost:5173")
    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND,
        shell=True,
    )


def main():
    banner()

    # Check Python version
    pv = sys.version_info
    check(pv >= (3, 8), f"Python {pv.major}.{pv.minor}.{pv.micro}", fatal=True)

    # Check .env
    if not ENV_FILE.exists():
        if ENV_EXAMPLE.exists():
            print(f"  ! .env not found. Copying from .env.example…")
            import shutil
            shutil.copy(ENV_EXAMPLE, ENV_FILE)
            print(f"  ✓ Created .env — edit it to set DATABASE_URL, ANTHROPIC_API_KEY, etc.")
        else:
            check(False, ".env file not found — create it from .env.example", fatal=True)
    else:
        check(True, ".env exists")

    # Load .env
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)

    # Check DB
    print("\n▸ Checking environment…")
    try:
        from backend.app.db.session import check_db_connection
        db_ok = check_db_connection()
    except Exception:
        db_ok = False
    check(db_ok, "PostgreSQL connection" + ("" if db_ok else " — start PostgreSQL and set DATABASE_URL in .env"))

    # Check Ollama
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        ollama_ok = r.status_code == 200
    except Exception:
        ollama_ok = False
    check(ollama_ok, "Ollama available" + ("" if ollama_ok else " — run: ollama serve"))

    # Run migration if DB is available
    if db_ok:
        run_migration()
    else:
        print("\n  ⚠ Skipping migration (no DB connection).")
        print("  Start PostgreSQL and re-run this script.\n")

    # Start processes
    procs = []
    use_frontend = "--frontend" in sys.argv

    backend = start_backend()
    procs.append(backend)

    if use_frontend:
        time.sleep(1)
        frontend = start_frontend()
        procs.append(frontend)
        print(f"  Frontend: http://localhost:5173\n")

    try:
        for p in procs:
            if p is not None:
                p.wait()
    except KeyboardInterrupt:
        print("\n\nShutting down…")
        for p in procs:
            if p is not None:
                p.terminate()
        sys.exit(0)


if __name__ == "__main__":
    main()
