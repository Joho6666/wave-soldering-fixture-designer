"""
Wave Soldering Fixture Designer — Local Launcher
Starts the FastAPI backend and opens the browser to the local UI.

Usage:
    python launcher.py

Requirements:
    - Python 3.11+ with dependencies from backend/requirements.txt installed
    - Frontend built to dist/ (npm run build)
"""
import os
import sys
import time
import signal
import subprocess
import webbrowser
from pathlib import Path


def find_project_root() -> Path:
    """Find the project root directory relative to this script."""
    script_dir = Path(__file__).resolve().parent
    if (script_dir.parent / "backend").exists():
        return script_dir.parent
    if (script_dir / "backend").exists():
        return script_dir
    print("Error: Cannot locate project root (expected backend/ directory).")
    sys.exit(1)


def find_python(project_root: Path) -> str:
    """Find Python executable, preferring the venv."""
    venv_python = project_root / "backend" / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    venv_python_unix = project_root / "backend" / ".venv" / "bin" / "python"
    if venv_python_unix.exists():
        return str(venv_python_unix)
    return sys.executable


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

    if dist_dir.exists():
        os.environ["STATIC_DIR"] = str(dist_dir)
        print(f"  Frontend: Serving from {dist_dir}")
    else:
        print("  Frontend: dist/ not found — run 'npm run build' first")
        print("            Or access frontend dev server at http://localhost:3000")

    print()
    print("Starting backend server...")
    print("Press Ctrl+C to stop.\n")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_dir)

    proc = subprocess.Popen(
        [
            python_exe, "-m", "uvicorn",
            "app.main:app",
            "--host", host,
            "--port", str(port),
            # Production mode: no --reload
        ],
        cwd=str(backend_dir),
        env=env,
    )

    time.sleep(2)

    url = f"http://{host}:{port}"
    if dist_dir.exists():
        print(f"Opening browser at {url} ...")
        webbrowser.open(url)
    else:
        dev_url = "http://localhost:3000"
        print(f"Opening browser at {dev_url} (dev server) ...")
        webbrowser.open(dev_url)

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
        print("Server stopped.")


if __name__ == "__main__":
    main()
