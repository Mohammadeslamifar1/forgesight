"""Run the real fitted model against a temporary inspection database for browser tests."""

import shutil
import tempfile
from pathlib import Path

import uvicorn

from forgesight.api import create_app
from forgesight.paths import ARTIFACTS, DATA

if __name__ == "__main__":
    if not (ARTIFACTS / "active.json").exists():
        raise SystemExit("Fit and evaluate the model before running the real-model browser tests.")
    with tempfile.TemporaryDirectory(prefix="forgesight-e2e-") as temporary:
        root = Path(temporary)
        shutil.copytree(
            DATA / "datasets" / "bottle" / "test", root / "datasets" / "bottle" / "test"
        )
        application = create_app(root, ARTIFACTS)
        uvicorn.run(application, host="127.0.0.1", port=8011)
