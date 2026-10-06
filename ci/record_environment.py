"""Record the tested source identity and dependency versions on a CI runner."""
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import subprocess

import pyEDM


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    imported = Path(pyEDM.__file__).resolve()
    assert imported == root / "src/pyEDM/__init__.py", imported
    report = {"python": platform.python_version(), "platform": platform.platform(),
              "import_origin": str(imported), "github_sha": os.environ.get("GITHUB_SHA"),
              "checkout_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "versions": {name: version(name) for name in
                           ("pyEDM", "numpy", "scipy", "pandas", "scikit-learn", "pytest")}}
    output = root / "test-results"
    output.mkdir(exist_ok=True)
    (output / "environment.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
