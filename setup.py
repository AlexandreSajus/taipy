# Copyright 2023 Avaiga Private Limited
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

"""The setup script."""

import json
import os
from pathlib import Path

from setuptools import find_namespace_packages, find_packages, setup
from setuptools.command.build_py import build_py

with open("README.md") as readme_file:
    readme = readme_file.read()

with open(f"src{os.sep}taipy{os.sep}version.json") as version_file:
    version = json.load(version_file)
    version_string = f'{version.get("major", 0)}.{version.get("minor", 0)}.{version.get("patch", 0)}'
    if vext := version.get("ext"):
        version_string = f"{version_string}.{vext}"

requirements = [
    "taipy-gui@git+https://git@github.com/Avaiga/taipy-gui.git@develop",
    "taipy-rest@git+https://git@github.com/Avaiga/taipy-rest.git@develop",
]

test_requirements = ["pytest>=3.8"]

extras_require = {
    "ngrok": ["pyngrok>=5.1,<6.0"],
    "image": [
        "python-magic>=0.4.24,<0.5;platform_system!='Windows'",
        "python-magic-bin>=0.4.14,<0.5;platform_system=='Windows'",
    ],
    "rdp": ["rdp>=0.8"],
    "arrow": ["pyarrow>=10.0.1,<11.0"],
    "mssql": ["pyodbc>=4"],
}


def _build_webapp():
    already_exists = Path("./src/taipy/gui_core/lib/taipy-gui-core.js").exists()
    if not already_exists:
        os.system("cd gui && npm ci && npm run build")


class NPMInstall(build_py):
    def run(self):
        _build_webapp()
        build_py.run(self)


setup(
    author="Avaiga",
    author_email="dev@taipy.io",
    python_requires=">=3.8",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    description="A 360° open-source platform from Python pilots to production-ready web apps.",
    install_requires=requirements,
    license="Apache License 2.0",
    long_description=readme,
    long_description_content_type="text/markdown",
    keywords="taipy",
    name="taipy",
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src") + find_packages(include=["taipy"]),
    include_package_data=True,
    test_suite="tests",
    url="https://github.com/avaiga/taipy",
    version=version_string,
    zip_safe=False,
    extras_require=extras_require,
    cmdclass={"build_py": NPMInstall},
)
