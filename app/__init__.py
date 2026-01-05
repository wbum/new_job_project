import os

"""Shim package: expose workflow_service/app as top-level package "app".
This lets existing tests/imports that use "app.*" work without copying code.
"""

# Prepend workflow_service/app to this package path
__path__.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "workflow_service", "app")))
