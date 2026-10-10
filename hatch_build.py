"""Fail clearly if Hatch's implicit files exceed the explicit distribution list."""

from pathlib import Path
from tarfile import open as open_tar
from zipfile import ZipFile
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def finalize(self, version, build_data, artifact_path):
        path = Path(artifact_path)
        if self.target_name == "sdist":
            allowed = {
                name.lstrip("/") for name in self.build_config.target_config["include"]
            } | {"PKG-INFO"}
            with open_tar(path) as archive:
                actual = {
                    "/".join(Path(member.name).parts[1:])
                    for member in archive.getmembers()
                    if member.isfile()
                }
                if any(
                    not (member.isfile() or member.isdir())
                    for member in archive.getmembers()
                ):
                    path.unlink()
                    raise RuntimeError("distribution contains unsupported link entries")
        else:
            allowed = {
                name.removeprefix("src/")
                for name in self.build_config.target_config["only-include"]
            }
            info = (
                self.metadata.core.name.replace("-", "_")
                + "-"
                + self.metadata.version
                + ".dist-info/"
            )
            allowed |= {
                info + name
                for name in (
                    "METADATA",
                    "WHEEL",
                    "entry_points.txt",
                    "licenses/LICENSE",
                    "RECORD",
                )
            }
            with ZipFile(path) as archive:
                actual = {name for name in archive.namelist() if not name.endswith("/")}
        if actual != allowed:
            path.unlink()
            raise RuntimeError("distribution file list differs from explicit allowlist")
