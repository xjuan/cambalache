"""
Test project export xml for Merengue
"""
import os
from cambalache import CmbProject, config
from gi.repository import GObject, Gtk
from lxml import etree


def cmb_workspace_default_test(target_tk, type_class, ws_properties):
    """
        Check type_class has ws_properties by default
    """
    project = CmbProject(target_tk=target_tk)

    # Add an UI
    ui = project.add_ui("workspace_defaults.ui")

    # Create object with workspace defaults
    obj = project.add_object(ui.ui_id, type_class)
    assert(obj is not None)

    # Export UI file in merengue mode (Workspace)
    str_exported = project.db.tostring(ui.ui_id, merengue=True)

    # Check export worked
    assert(str_exported is not None)

    # Parse results
    root = etree.fromstring(str_exported.encode())

    # Find object node
    obj_node = root.find(f"object[@class='{type_class}']")
    assert(obj_node is not None)

    for property_id, value, exp in ws_properties:
        # Look for a property node with name==property_id
        prop = obj_node.find(f'property[@name="{property_id}"]')
        assert(prop is not None)

        # Check value
        if value:
            assert(prop.text==value)

        # Check property xpath expression
        if exp:
            assert(len(prop.xpath(exp)) > 0)


def test_object_id():
    """
        Make sure merengue output has object ids in the form __cmb__{ui_id}.{object_id}
    """
    project = CmbProject(target_tk='gtk-4.0')

    # Add an UI
    ui = project.add_ui("test.ui")

    objects = []

    # GtkWindow
    win = project.add_object(ui.ui_id, "GtkWindow", "window")
    assert(win is not None)
    objects.append(win)

    # GtkBox
    box = project.add_object(ui.ui_id, "GtkBox", "box", parent_id=win.object_id)
    assert(box is not None)
    objects.append(box)

    # GtkButton
    button = project.add_object(ui.ui_id, "GtkButton", "button", parent_id=box.object_id)
    assert(button is not None)
    objects.append(button)

    # Export UI file in merengue mode (Workspace)
    str_exported = project.db.tostring(ui.ui_id, merengue=True)

    # Check export worked
    assert(str_exported is not None)

    builder = Gtk.Builder()
    builder.add_from_string(str_exported)

    for obj in objects:
        gobject = builder.get_object(f"__cmb__{ui.ui_id}.{obj.object_id}")
        assert(gobject is not None)
        assert(GObject.type_name(type(gobject))==obj.type_id)


def test_no_signals():
    """
        Make sure merengue output does not have signals declaration to avoid GtkBuilder errors not finding the callbacks
    """
    path = os.path.join(os.path.dirname(__file__), "gtk+-3.0", "signals.ui")

    project = CmbProject(target_tk="gtk+-3.0")
    ui_id = project.db.import_file(path)
    str_exported = project.db.tostring(ui_id, merengue=True)

    root = etree.fromstring(str_exported.encode())

    assert(root.find(f"signal") is None)


def test_gtk4_stack_page_workspace_default():
    cmb_workspace_default_test("gtk-4.0", "GtkStackPage",
        [("child", None, "object[@class='GtkLabel']/property[@name='label' and text()='Empty Page']")]
    )

