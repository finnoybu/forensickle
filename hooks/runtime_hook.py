import sys
import os
# Ensure the _internal directory is on the path for local packages
base = os.path.dirname(os.path.abspath(sys.executable))
internal = os.path.join(base, '_internal')
if os.path.isdir(internal) and internal not in sys.path:
    sys.path.insert(0, internal)
# Also add the base dir
if base not in sys.path:
    sys.path.insert(0, base)
