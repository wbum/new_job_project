import os

# Ensure the "workflow_service/app" directory is searched for submodules of the top-level "app" package.
# This lets `import app.models` resolve to workflow_service/app/models.
_pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'workflow_service', 'app'))
if _pkg_dir not in __path__:
    __path__.insert(0, _pkg_dir)

__all__ = []
