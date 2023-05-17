"""
Test CmbObject API
"""
import os

from cambalache import CmbProject, config


def cmb_catalog_data_test(target_tk):
    # Create new project
    project = CmbProject(target_tk=target_tk)

    # Check for a known iface
    row = project.db.execute("SELECT parent_id FROM type WHERE type_id='GtkOrientable';").fetchall()
    assert(row is not None)
    assert(len(row) == 1)
    assert(row[0][0] == "interface")

    # Check a know iface property
    row = project.db.execute("SELECT property_id FROM property WHERE owner_id='GtkOrientable' AND property_id='orientation';").fetchall()
    assert(row is not None)
    assert(len(row) == 1)

    # Check a type has the iface
    row = project.db.execute("SELECT iface_id FROM type_iface WHERE type_id='GtkBox' AND iface_id='GtkOrientable';").fetchall()
    assert(row is not None)
    assert(len(row) == 1)


def test_gtk3_project_catalogs_data():
    cmb_catalog_data_test("gtk+-3.0")


def test_gtk4_project_catalogs_data():
    cmb_catalog_data_test("gtk-4.0")
