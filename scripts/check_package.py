"""Build distributions and run tests against an isolated wheel installation."""

import email
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=ROOT):
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def main():
    with tempfile.TemporaryDirectory(prefix="notcologger-package-") as temporary:
        work = Path(temporary)
        dist = work / "dist"
        # build creates the wheel from the sdist, checking that it is buildable.
        run(sys.executable, "-m", "build", "--outdir", dist)
        wheel, = dist.glob("*.whl")
        sdist, = dist.glob("*.tar.gz")
        run(sys.executable, "-m", "twine", "check", "--strict", wheel, sdist)
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert "notcologger/__init__.py" in names
            assert any(name.endswith("/licenses/LICENSE") for name in names)
            metadata_name, = (name for name in names if name.endswith("/METADATA"))
            metadata = email.message_from_bytes(archive.read(metadata_name))
            assert metadata["Requires-Python"] == ">=3.11,<4.0"
            assert metadata["License-Expression"] == "MIT"
            assert "# Not-co-logger" in metadata.get_payload()
        with tarfile.open(sdist) as archive:
            names = {name.split("/", 1)[-1] for name in archive.getnames()}
            assert {"README.md", "LICENSE", "pyproject.toml",
                    "notcologger/__init__.py"} <= names
        environment = work / "venv"
        venv.create(environment, with_pip=True)
        python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        run(python, "-m", "pip", "install", "--no-deps", wheel, cwd=work)
        run(python, "-I", "-c",
            "import notcologger; print('Testing installed package:', notcologger.__file__)",
            cwd=work)
        run(python, "-I", "-m", "unittest", "discover", "-s", ROOT / "tests", "-v",
            cwd=work)


if __name__ == "__main__":
    main()
