import os

# Make the package 'app' delegate submodule resolution to workflow_service/app
# so imports like `import app.main` will resolve to workflow_service/app/main.py
__path__ = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workflow_service", "app"))
]
