#
# Blueprint compiler integration functions
#
# Copyright (C) 2025  Juan Pablo Ugarte
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
# SPDX-License-Identifier: LGPL-2.1-only
#

import io

try:
    import blueprintcompiler as bp
    from blueprintcompiler import parser, tokenizer
    from blueprintcompiler.decompiler import decompile_string
    from blueprintcompiler.outputs import XmlOutput
except Exception:
    bp = None


class CmbBlueprintError(Exception):
    def __init__(self, message, errors=[]):
        super().__init__(message)
        self.errors = errors


class CmbBlueprintUnsupportedError(CmbBlueprintError):
    pass


class CmbBlueprintMissingError(CmbBlueprintError):
    def __init__(self):
        super().__init__("blueprintcompiler is not available")


def cmb_blueprint_decompile(data: str) -> str:
    if bp is None:
        raise CmbBlueprintMissingError()

    try:
        retval = decompile_string(data)
    except bp.decompiler.UnsupportedError as e:
        raise CmbBlueprintUnsupportedError(str(e))
    except Exception as e:
        raise CmbBlueprintError(str(e))

    return retval


def cmb_blueprint_compile(data: str) -> str:
    if bp is None:
        raise CmbBlueprintMissingError()

    tokens = tokenizer.tokenize(data)
    ast, errors, warnings = parser.parse(tokens)

    if errors:
        f = io.StringIO("")
        errors.pretty_print("temp", data, f)
        f.seek(0)
        raise CmbBlueprintError(f.read(), errors=errors)

    if ast is None:
        raise CmbBlueprintError("AST is None")

    # Ignore warnings

    retval = XmlOutput().emit(ast)
    return retval.encode()

