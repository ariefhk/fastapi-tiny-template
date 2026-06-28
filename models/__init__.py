import importlib
import pkgutil

import models

for _mod in pkgutil.iter_modules(models.__path__):
    if _mod.name.endswith("_model"):
        importlib.import_module(f"models.{_mod.name}")
