import os
import sys

from gi.repository import GObject

basedir = os.path.dirname(__file__) or "."
sys.path.append(os.path.join(basedir, "../../"))

from cambalache import CmbProject, CmbView, CmbTreeView, CmbUIEditor, CmbUIRequiresEditor, CmbObjectEditor, CmbSignalEditor
from cambalache import CmbTypeChooser, CmbTypeChooserPopover, CmbTypeChooserWidget

# Ensure types that we are going to use in Glade
GObject.type_ensure(CmbProject)
GObject.type_ensure(CmbView)
GObject.type_ensure(CmbTreeView)
GObject.type_ensure(CmbUIEditor)
GObject.type_ensure(CmbUIRequiresEditor)
GObject.type_ensure(CmbObjectEditor)
GObject.type_ensure(CmbSignalEditor)
GObject.type_ensure(CmbTypeChooser)
GObject.type_ensure(CmbTypeChooserPopover)
GObject.type_ensure(CmbTypeChooserWidget)
