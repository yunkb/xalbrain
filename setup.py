"""Install module."""
import subprocess
from pathlib import Path
from setuptools import setup, Command

from typing import List


class SphinxCommand(Command):
    """Command to build the documentation."""

    user_options: List[str] = []
    description = "Build html doc."

    def initialize_options(self):
        """Initialise options."""
        self.sphinx_source = Path.cwd() / "doc" / "source"
        self.sphinx_build = Path.cwd() / "doc" / "build"

    def finalize_options(self):
        """finalize options."""
        if self.sphinx_source:
            msg = f"sphinx source folder {self.sphinx_source} do not exist"
            assert self.sphinx_source.exists(), msg

    def run(self):
        """Execute command."""
        cmd = f"sphinx-build -b html -na {self.sphinx_source} {self.sphinx_build}"
        subprocess.check_call(cmd)


CMDS = {
    "sphinx": SphinxCommand,
}


setup(
    name = "xalbrain",
    author = "Jakob E. Schreiner",
    author_email = "jakob@xal.no",
    packages = ["xalbrain", "xalbrain.cellmodels",],
    package_dir = {"xalbrain": "xalbrain"},
    cmdclass = CMDS
)
