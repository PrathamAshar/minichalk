"""Start both local services; terminate both when either exits or Ctrl-C is pressed."""

import os
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
children: list[subprocess.Popen] = []


def stop(*_):
    for child in children:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
    for child in children:
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()


if __name__ == "__main__":

    def terminate(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, terminate)
    try:
        children.append(
            subprocess.Popen(
                [
                    str(ROOT / "backend" / ".venv" / "bin" / "python"),
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--reload",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=ROOT / "backend",
                start_new_session=True,
            )
        )
        children.append(
            subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=ROOT / "frontend",
                start_new_session=True,
            )
        )
        print(
            "Console: http://localhost:3000   API: http://localhost:8000/docs",
            flush=True,
        )
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop()
