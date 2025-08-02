#!/usr/bin/pytest

"""
import .ui files into cambalache and export to compare results
"""
import os
import pytest

from cambalache import CmbProject, config


@pytest.mark.parametrize("target_tk,filename", [
    ("gtk+-3.0", "window.ui"),
    ("gtk+-3.0", "children.ui"),
    ("gtk+-3.0", "packing.ui"),
    ("gtk+-3.0", "signals.ui"),
    ("gtk+-3.0", "template.ui"),
    ("gtk+-3.0", "comboboxtext.ui"),
    ("gtk+-3.0", "dialog.ui"),
    ("gtk+-3.0", "label.ui"),
    ("gtk+-3.0", "levelbar.ui"),
    ("gtk+-3.0", "liststore.ui"),
    ("gtk+-3.0", "scale.ui"),
    ("gtk+-3.0", "sizegroup.ui"),
    ("gtk+-3.0", "style.ui"),
    ("gtk+-3.0", "treestore.ui"),
    ("gtk+-3.0", "filefilter.ui"),
    ("gtk+-3.0", "custom_fragment.ui"),
    ("gtk+-3.0", "bindings.ui"),
    ("gtk+-3.0", "menu.ui"),
    ("gtk+-3.0", "accessibility.ui"),
    ("gtk-4.0", "window.ui"),
    ("gtk-4.0", "children.ui"),
    ("gtk-4.0", "layout.ui"),
    ("gtk-4.0", "signals.ui"),
    ("gtk-4.0", "template.ui"),
    ("gtk-4.0", "inline_object.ui"),
    ("gtk-4.0", "stack_page.ui"),
    ("gtk-4.0", "liststore.ui"),
    ("gtk-4.0", "treestore.ui"),
    ("gtk-4.0", "comboboxtext.ui"),
    ("gtk-4.0", "style.ui"),
    ("gtk-4.0", "label.ui"),
    ("gtk-4.0", "filefilter.ui"),
    ("gtk-4.0", "custom_fragment.ui"),
    ("gtk-4.0", "bindings.ui"),
    ("gtk-4.0", "menu.ui"),
    ("gtk-4.0", "string_list.ui"),
    ("gtk-4.0", "accessibility.ui"),
    ("gtk-4.0", "ui_comments.ui"),
    ("gtk-4.0", "expression.ui"),
])
def test_(target_tk, filename):
    """
    import .ui file and compare it with the exported version
    """
    path = os.path.join(os.path.dirname(__file__), target_tk, filename)
    str_original = open(path, "r").read()

    project = CmbProject(target_tk=target_tk)
    ui, msgs, detail_msg = project.import_file(path)

    assert (ui)
    assert (msgs is None)
    assert (detail_msg is None)

    str_exported = project.db.tostring(ui.ui_id)

    # Remove "Created with" comment since version will not match
    str_exported = str_exported.replace(f"<!-- Created with Cambalache {config.VERSION} -->\n", "")

    assert str_exported == str_original

