#
# uitls - Cambalache utilities
#
# Copyright (C) 2023  Juan Pablo Ugarte
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.
#
# library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# Authors:
#   Juan Pablo Ugarte <juanpablougarte@gmail.com>
#

def parse_version(version):
    return tuple([int(x) for x in version.split(".")])


def version_cmp(a, b):
    an = len(a)
    bn = len(a)

    for i in range(0, max(an, bn)):
        val_a = a[i] if i < an else 0
        val_b = b[i] if i < bn else 0
        retval = val_a - val_b

        if retval != 0:
            return retval

    return 0


def version_cmp_str(a, b):
    return version_cmp(parse_version(a), parse_version(b))
