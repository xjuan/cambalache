#!/bin/python3
#
# update-supporters - Cambalache supporters list tool
#
# Copyright (C) 2021  Juan Pablo Ugarte
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as
# published by the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Authors:
#   Juan Pablo Ugarte <juanpablougarte@gmail.com>
#

import sys
import csv


header_text = """# Cambalache supporters

Many thanks to all the people that suppport the project

"""


def get_supporters(filename):
    retval = []

    with open(filename, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Name"]
            lifetime = float(row["Lifetime Amount"])

            if lifetime > 0:
                retval.append((name, lifetime))

    return [x[0] for x in sorted(retval, key=lambda v: v[1], reverse=True)]


def save_supporters(fd, supporters, prefix):
    for name in supporters:
        fd.write(f"{prefix} {name}\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} input.csv output.md")
        exit()

    supporters = get_supporters(sys.argv[1])

    with open(sys.argv[2], "w") as fd:
        fd.write(header_text)
        save_supporters(fd, supporters, " - ")
        fd.close()
