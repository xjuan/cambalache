#!/usr/bin/pytest

import os

from cambalache import CmbProject


def enum_and_flags_test(widget_name):
    project = CmbProject(target_tk="gtk-4.0")
    project.import_file(os.path.join(os.path.dirname(__file__), "gtk-4.0", "enum_and_flags.ui"))

    widget = project.get_object_by_name(1, widget_name)
    input_hints = widget.properties_dict["input-hints"]
    assert (input_hints)
    assert (input_hints.value == "emoji|lowercase|private")

    input_purpose = widget.properties_dict["input-purpose"]
    assert (input_purpose)
    assert (input_purpose.value == "digits")

    valign = widget.properties_dict["valign"]
    assert (valign)
    assert (valign.value == "center")


def test_enum_and_flags_as_nick():
    enum_and_flags_test("nick")


def test_enum_and_flags_as_name():
    enum_and_flags_test("name")


def test_enum_and_flags_as_nick_and_name():
    enum_and_flags_test("nick_name")


def test_enum_and_flags_as_integer_values():
    enum_and_flags_test("integer")
