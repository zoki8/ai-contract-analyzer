import os
import threading
import time

import uvicorn

from main import app


def exit_when_parent_dies():
    """Stop the backend when the app that started it is gone."""
    parent = os.getppid()
    while True:
        time.sleep(1)
        if os.getppid() != parent:
            os._exit(0)


if __name__ == "__main__":
    threading.Thread(target=exit_when_parent_dies, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)