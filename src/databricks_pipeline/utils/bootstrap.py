"""Bootstrap helpers so Databricks notebooks can import this package."""

from __future__ import annotations

import sys
from pathlib import Path


# Common workspace locations for this repo (Repos / Users Git folders).
_DEFAULT_CANDIDATES = (
    Path.cwd() / "src",
    Path.cwd().parent / "src",
    Path("/Workspace/Users/emyraeleson@gmail.com/databricks-pipeline_flow/src"),
    Path("/Workspace/Repos/databricks_pipeline/src"),
)


def ensure_package_on_path(
    extra_candidates: list[str | Path] | None = None,
) -> str:
    """Insert the repo ``src`` directory on ``sys.path`` if needed.

    Returns the path that was used (or already present).
    """
    try:
        import databricks_pipeline  # noqa: F401

        return str(Path(databricks_pipeline.__file__).resolve().parent.parent)
    except ImportError:
        pass

    candidates: list[Path] = []
    if extra_candidates:
        candidates.extend(Path(p) for p in extra_candidates)
    candidates.extend(_DEFAULT_CANDIDATES)

    for candidate in candidates:
        package_init = candidate / "databricks_pipeline" / "__init__.py"
        if package_init.is_file():
            path = str(candidate.resolve())
            if path not in sys.path:
                sys.path.insert(0, path)
            return path

    raise ModuleNotFoundError(
        "databricks_pipeline not found. Sync this repo to Databricks and "
        "ensure src/databricks_pipeline is available, or pip-install the package."
    )
