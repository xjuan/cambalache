#!/usr/bin/python3

import sys
from tools.cmb_init_dev import cmb_init_dev

if __name__ == "__main__":
    cmb_init_dev()

    from cambalache.app import CmbApplication

    app = CmbApplication()
    app.run(sys.argv)
