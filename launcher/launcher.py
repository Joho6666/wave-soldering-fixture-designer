"""
Wave Soldering Fixture Designer — Local Launcher
Starts the FastAPI backend and serves the built frontend from dist/.

Usage (from repository root):
    python launcher/launcher.py

Requirements:
    - Python 3.11+ with backend/.venv and backend/requirements.txt
    - Frontend built to dist/ (`npm run build`)
"""
from __future__ import annotations

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path


def find_project_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    if (script_dir.parent / "backend").exists():
        return script_dir.parent
    if (script_dir / "backend").exists():
        return script_dir
    print("Error: Cannot locate project root (expected backend/ directory).")
    sys.exit(1)


def find_python(project_root: Path) -> str:
    venv_python = project_root / "backend" / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    venv_python_unix = project_root / "backend" / ".venv" / "bin" / "python"
    if venv_python_unix.exists():
        return str(venv_python_unix)
    return sys.executable


def stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main():
    project_root = find_project_root()
    backend_dir = project_root / "backend"
    dist_dir = project_root / "dist"
    python_exe = find_python(project_root)
    host = "127.0.0.1"
    port = 8000

    print("=" * 50)
    print("  Wave Soldering Fixture Designer")
    print("  波峰焊治具自动出图系统")
    print("=" * 50)
    print(f"  Backend: {backend_dir}")
    print(f"  Python:  {python_exe}")
    print(f"  Server:  http://{host}:{port}")
    print()

    if not dist_dir.exists() or not (dist_dir / "index.html").exists():
        print("  Frontend dist/ is missing.")
        print("  Build the UI first:")
        print("      npm ci")
        print("      npm run build")
        print("  Then run this launcher again.")
        sys.exit(1)

    os.environ["STATIC_DIR"] = str(dist_dir)
    print(f"  Frontend: {dist_dir}")
    print()
    print("Starting backend + static UI...")
    print("Press Ctrl+C to stop.\n")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_dir)
    env["STATIC_DIR"] = str(dist_dir)
    env.setdefault("DEBUG", "false")

    proc = subprocess.Popen(
        [
            python_exe, "-m", "uvicorn",
            "app.main:app",
            "--host", host,
            "--port", str(port),
        ],
        cwd=str(backend_dir),
        env=env,
    )

    try:
        time.sleep(2)
        if proc.poll() is not None:
            print("Backend failed to start. Check Python dependencies in backend/.venv")
            sys.exit(proc.returncode or 1)
        url = f"http://{host}:{port}"
        print(f"Opening browser at {url} ...")
        webbrowser.open(url)
        proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        stop_process(proc)
        print("Server stopped.")


if __name__ == "__main__":
    main()
