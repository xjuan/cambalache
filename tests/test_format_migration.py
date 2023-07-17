#!/usr/bin/pytest

"""
Test Old format loading
"""
import os

from cambalache import CmbProject

basedir = os.path.dirname(__file__)


def migration_test(target, filename):
    project_path = os.path.join(basedir, target, filename)
    project = CmbProject(filename=project_path)

    assert project is not None


def test_gtk3_format_0_10_3():
    migration_test("gtk+-3.0", "test_project_0.10.3.cmb")


def test_gtk4_format_0_10_3():
    migration_test("gtk-4.0", "test_project_0.10.3.cmb")
