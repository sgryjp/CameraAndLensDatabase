#!/bin/env python
from pathlib import Path
from subprocess import check_call

if __name__ == "__main__":
    assert Path(__file__).parent.name == "tools"
    root = Path(__file__).parent.parent

    dirs = ["camera_lens_database", "tools"]
    check_call(["flake8"] + dirs, cwd=root)
    check_call(["mypy"] + dirs, cwd=root)
