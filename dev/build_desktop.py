"""Build native Windows and Linux desktop distributions (run on the target OS)."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import iconik_locator as loc


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
VERSION = loc.VERSION
TAG = "v" + VERSION.replace(".", "_")


def run(*args):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


def build():
    if sys.platform not in ("win32", "linux"):
        raise SystemExit("Run this builder on Windows or Linux.")
    from PIL import Image

    windows = sys.platform == "win32"
    platform_name = "windows_x86_64" if windows else "linux_x86_64"
    name = f"Iconik Locator {VERSION}" if windows else f"iconik-locator-{VERSION}"
    icon = ROOT / "assets" / ("app_icon.ico" if windows else "app_icon_source.png")
    if windows:
        Image.open(ROOT / "assets/app_icon_source.png").save(icon, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", name,
            "--icon", str(icon), "--collect-all", "keyring", "--distpath", str(DIST)]
    if windows:
        resource = ROOT / "build/windows_version.txt"
        resource.parent.mkdir(exist_ok=True)
        version_tuple = tuple(int(v) for v in VERSION.split(".")) + (0,)
        resource.write_text(
            f"VSVersionInfo(ffi=FixedFileInfo(filevers={version_tuple!r}, prodvers={version_tuple!r}, mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)), "
            f"kids=[StringFileInfo([StringTable('040904B0', [StringStruct('FileDescription', 'Iconik Storage Locator'), StringStruct('FileVersion', '{VERSION}'), StringStruct('ProductName', 'Iconik Storage Locator'), StringStruct('ProductVersion', '{VERSION}')])]), VarFileInfo([VarStruct('Translation', [1033,1200])])])",
            encoding="utf-8")
        args += ["--version-file", str(resource)]
    args.append(str(ROOT / "iconik_locator_gui.py"))
    run(*args)
    folder = DIST / name
    binary = folder / (name + ".exe" if windows else name)
    report = DIST / "gui-smoke.json"
    run(binary, "--smoke-test", report)
    if json.loads(report.read_text())["version"] != VERSION:
        raise RuntimeError("Packaged GUI version mismatch")
    (folder / "READ_ME.txt").write_text(
        f"Iconik Storage Locator {VERSION}\n\n"
        + (f"Extract the entire zip, then double-click {name}.exe. Keep the _internal folder beside the exe.\n" if windows else f"Extract the archive, then open {name}. If needed, allow it to run as a program in file Properties > Permissions.\n")
        + "Enter your Iconik App-ID and Auth-Token. Click Test API Access, paste an Iconik link, and click Locate.\n"
        "Output defaults to S3. Use Copy S3 Only to copy paths.\n"
        "Bulk Lookup accepts pasted links or CSV/XLSX with column header iconik_url. Export CSV or XLSX.\n"
        "Credentials are saved only in your system credential store; never in GitHub. Linux users must unlock their login keyring.\n",
        encoding="utf-8")
    artifacts = []
    archive_base = DIST / f"Iconik_Locator_App_{TAG}_{platform_name}"
    if windows:
        artifacts.append(Path(shutil.make_archive(str(archive_base), "zip", DIST, name)))
    else:
        archive = Path(str(archive_base) + ".tar.gz")
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(folder, arcname=name)
        artifacts.append(archive)
        package = ROOT / "build/deb"
        if package.exists():
            shutil.rmtree(package)
        (package / "DEBIAN").mkdir(parents=True)
        install = package / "opt/iconik-locator"
        shutil.copytree(folder, install)
        (package / "DEBIAN/control").write_text(
            f"Package: iconik-locator\nVersion: {VERSION}\nArchitecture: amd64\n"
            "Maintainer: Michael Brandon Falk\nSection: utils\nPriority: optional\n"
            "Depends: libc6 (>= 2.35), libx11-6, libxext6, libxrender1, libxft2, libfontconfig1, libfreetype6, gnome-keyring\n"
            "Description: Locate S3 and storage paths for Iconik assets\n", encoding="utf-8")
        desktop = package / "usr/share/applications/iconik-locator.desktop"
        desktop.parent.mkdir(parents=True)
        desktop.write_text(f"[Desktop Entry]\nType=Application\nName=Iconik Locator\nExec=/opt/iconik-locator/{name}\nIcon=iconik-locator\nTerminal=false\nCategories=Utility;\n", encoding="utf-8")
        image = package / "usr/share/icons/hicolor/256x256/apps/iconik-locator.png"
        image.parent.mkdir(parents=True)
        Image.open(icon).resize((256, 256)).save(image)
        deb = DIST / f"Iconik_Locator_App_{TAG}_linux_amd64.deb"
        run("dpkg-deb", "--root-owner-group", "--build", package, deb)
        artifacts.append(deb)
    checksums = DIST / f"checksums_{platform_name}.txt"
    checksums.write_text("".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in artifacts), encoding="utf-8")
    print("\n".join(str(p) for p in artifacts + [checksums]))


if __name__ == "__main__":
    build()
