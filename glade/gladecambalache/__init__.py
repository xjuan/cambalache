import os
import sys

basedir = os.path.dirname(__file__) or '.'
sys.path.append(os.path.join(basedir, '../../'))

from cambalache import *

# Ensure types that we are going to use in Glade
GObject.type_ensure(CmbProject)
GObject.type_ensure(CmbProjectView)