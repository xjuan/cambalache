#!/usr/bin/python3
import sys
from tests.cmb_run_dev import get_app

if __name__ == "__main__":
    app = get_app()
    print(sys.argv)
    app.run(sys.argv)
