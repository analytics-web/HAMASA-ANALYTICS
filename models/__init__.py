import os
import importlib

# Automatically import all .py files in this folder (except __init__.py and base.py)
package_dir = os.path.dirname(__file__)
for filename in os.listdir(package_dir):
    if filename.endswith(".py") and filename not in {"__init__.py", "base.py"}:
        module_name = f"models.{filename[:-3]}"
        importlib.import_module(module_name)

# Import Base last so it's available here
from .base import Base
