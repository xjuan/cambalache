#!/usr/bin/pytest

"""
import .ui files into cambalache and compare it to blueprint compiler output
"""
import os
import pytest

from lxml import etree
from cambalache import CmbProject
from cambalache.cmb_blueprint import cmb_blueprint_decompile, cmb_blueprint_compile, CmbBlueprintUnsupportedError


def tostring(ui):
    db = ui.project.db

    # Internal API to ensure Cambalache outputs the same as blueprint compiler
    db._output_lowercase_boolean = True
    db._output_use_enum_value = True

    tree = db.export_ui(ui.ui_id)

    if tree is None:
        return None

    root = tree.getroot()

    # Remove all XML comments since they are not supported by blueprint
    for node in root.xpath("//comment()"):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)

    for node in root.iterfind("requires"):
        lib = node.get("lib", None)
        if lib != "gtk":
            root.remove(node)

    return etree.tostring(root, pretty_print=True, encoding="UTF-8").decode("UTF-8")


def get_exported_and_blueprint(filename):
    """
    import .ui file and compare it with the exported version
    """
    path = os.path.join(os.path.dirname(__file__), "gtk-4.0", filename)
    project = CmbProject(target_tk="gtk-4.0")
    ui, msgs, detail_msg = project.import_file(path)

    assert (ui)
    assert (msgs is None)
    assert (detail_msg is None)

    # Export Cambalache UI
    str_exported = tostring(ui)

    # Decompile and recompile UI to Blueprint
    blueprint_decompiled = cmb_blueprint_decompile(str_exported)
    blueprint_compiled = cmb_blueprint_compile(blueprint_decompiled)
    assert blueprint_compiled is not None

    # Remove blueprint DO NOT EDIT comment
    root = etree.fromstring(blueprint_compiled)
    blueprint_compiled = etree.tostring(root, pretty_print=True, encoding="UTF-8").decode("UTF-8")

    return str_exported, blueprint_compiled


@pytest.mark.parametrize("filename", [
    "window.ui",
    "children.ui",
    "layout.ui",
    "signals.ui",
    "template.ui",
    "inline_object.ui",
    "stack_page.ui",
    "comboboxtext.ui",
    "style.ui",
    "filefilter.ui",
    "menu.ui",

    # help-text is not an accessibility property
    "accessibility.ui",

    # bind-flags missing
    # "bindings.ui",

    # Translation comment missing
    # "string_list.ui",
])
def test_assert_exported_and_compiled(filename):
    """
    import .ui file and compare it with the exported version
    """
    str_exported, blueprint_compiled = get_exported_and_blueprint(filename)

    # Compare blueprint generated string with cambalache
    assert blueprint_compiled.strip() == str_exported.strip()


@pytest.mark.parametrize("filename", [
    "liststore.ui",
    "treestore.ui",
    "label.ui",
])
def test_assert_exported_and_compiled_unsupported(filename):
    with pytest.raises(CmbBlueprintUnsupportedError):
        str_exported, blueprint_compiled = get_exported_and_blueprint(filename)

