"""Exec the allowlisted generator; Linux terminates it if its owning worker dies."""

import ctypes
import os
import signal
import sys

if __name__ == "__main__":
    parent = os.getppid()
    if sys.platform == "linux":
        if ctypes.CDLL(None).prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
            raise SystemExit("Cannot bind generator lifetime to its owner")
        if os.getppid() != parent:
            raise SystemExit(1)
    os.execvp(sys.argv[1], sys.argv[1:])
