#!/usr/bin/env bash
set -euo pipefail

# Iconik Storage Locator build script.
#
# Runtime code is Python standard library only. PyInstaller is a build-time
# dependency used only to create standalone macOS executables.

APP_NAME="iconik_locator"
GUI_APP_NAME="Iconik Locator"
SRC="iconik_locator.py"
GUI_SRC="iconik_locator_gui.py"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST="${ROOT}/dist"
BUILD="${ROOT}/build"
VERSION="$(python3 - "$ROOT/$SRC" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
print(re.search(r'^VERSION = "([^"]+)"', text, re.M).group(1))
PY
)"
VERSION_TAG="v${VERSION//./_}"
export PYINSTALLER_CONFIG_DIR="${ROOT}/.pyinstaller"

die() { echo "ERROR: $*" >&2; exit 1; }
msg() { echo "== $* =="; }

ensure_pyinstaller() {
  local py="$1"
  "${py}" - <<'PY' >/dev/null 2>&1 || "${py}" -m pip install --upgrade pyinstaller
import PyInstaller  # noqa: F401
PY
}

ensure_build_venv() {
  local arch_name="$1"
  local base_py="$2"
  local venv_dir="${ROOT}/.venv-${arch_name}"
  local venv_py="${venv_dir}/bin/python"
  if [[ ! -x "$venv_py" ]]; then
    echo "== creating ${arch_name} build venv ==" >&2
    arch -"${arch_name}" "$base_py" -m venv "$venv_dir"
  fi
  ensure_pyinstaller "$venv_py" >&2
  echo "$venv_py"
}

detect_arm_python() {
  local c
  for c in \
    "${ROOT}/../releases/v2.0.3/venv-arm/bin/python" \
    "$(command -v python3 || true)" \
    "/opt/homebrew/bin/python3" \
    "/usr/local/bin/python3"; do
    [[ -x "$c" ]] || continue
    if arch -arm64 "$c" -c 'import platform; print(platform.machine())' 2>/dev/null | grep -q '^arm64$'; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

detect_x86_python() {
  local c
  for c in \
    "${ROOT}/../releases/v2.0.3/venv-x86/bin/python" \
    "/usr/local/bin/python3" \
    "$(command -v python3 || true)"; do
    [[ -x "$c" ]] || continue
    if arch -x86_64 "$c" -c 'import platform; print(platform.machine())' 2>/dev/null | grep -q '^x86_64$'; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

sign_if_possible() {
  local bin="$1"
  if command -v codesign >/dev/null 2>&1; then
    codesign --force --sign - "$bin" >/dev/null 2>&1 || true
  fi
}

cd "$ROOT"
[[ -f "$SRC" ]] || die "Source not found: $SRC"
[[ -f "$GUI_SRC" ]] || die "Source not found: $GUI_SRC"

rm -rf "$BUILD" "$DIST"
mkdir -p "$DIST"
ARTIFACTS=()
CHECKSUM_ARTIFACTS=()

ARM_PY="$(detect_arm_python || true)"
[[ -n "$ARM_PY" ]] || die "Could not find an arm64 Python 3. On Apple Silicon, install Homebrew Python."
ARM_PY="$(ensure_build_venv arm64 "$ARM_PY")"
msg "arm64 build using: ${ARM_PY}"
arch -arm64 "$ARM_PY" -m PyInstaller \
  --onefile \
  --clean \
  --name "${APP_NAME}_arm64" \
  --distpath "$DIST" \
  --workpath "${BUILD}/${APP_NAME}_arm64" \
  --specpath "$ROOT" \
  "$SRC"
sign_if_possible "${DIST}/${APP_NAME}_arm64"
file "${DIST}/${APP_NAME}_arm64"
ARTIFACTS+=("${APP_NAME}_arm64")
CHECKSUM_ARTIFACTS+=("${APP_NAME}_arm64")
arch -arm64 "$ARM_PY" -m PyInstaller \
  --windowed \
  --clean \
  --name "${GUI_APP_NAME} ${VERSION}_arm64" \
  --distpath "$DIST" \
  --workpath "${BUILD}/${APP_NAME}_gui_arm64" \
  --specpath "$ROOT" \
  "$GUI_SRC"
sign_if_possible "${DIST}/${GUI_APP_NAME} ${VERSION}_arm64.app"
ARTIFACTS+=("${GUI_APP_NAME} ${VERSION}_arm64.app")

X86_PY="$(detect_x86_python || true)"
if [[ -n "$X86_PY" ]]; then
  X86_PY="$(ensure_build_venv x86_64 "$X86_PY")"
  msg "x86_64 build using: ${X86_PY}"
  arch -x86_64 "$X86_PY" -m PyInstaller \
    --onefile \
    --clean \
    --name "${APP_NAME}_x86_64" \
    --distpath "$DIST" \
    --workpath "${BUILD}/${APP_NAME}_x86_64" \
    --specpath "$ROOT" \
    "$SRC"
  sign_if_possible "${DIST}/${APP_NAME}_x86_64"
  file "${DIST}/${APP_NAME}_x86_64"
  ARTIFACTS+=("${APP_NAME}_x86_64")
  CHECKSUM_ARTIFACTS+=("${APP_NAME}_x86_64")
  arch -x86_64 "$X86_PY" -m PyInstaller \
    --windowed \
    --clean \
    --name "${GUI_APP_NAME} ${VERSION}_x86_64" \
    --distpath "$DIST" \
    --workpath "${BUILD}/${APP_NAME}_gui_x86_64" \
    --specpath "$ROOT" \
    "$GUI_SRC"
  sign_if_possible "${DIST}/${GUI_APP_NAME} ${VERSION}_x86_64.app"
  ARTIFACTS+=("${GUI_APP_NAME} ${VERSION}_x86_64.app")
else
  echo "WARNING: Skipping x86_64 build; no Intel/Rosetta Python 3 was found." >&2
fi

msg "Packaging"
cd "$DIST"
if [[ -f "${APP_NAME}_arm64" ]]; then
  zip -q -r "${APP_NAME}_arm64.zip" "${APP_NAME}_arm64"
  ARTIFACTS+=("${APP_NAME}_arm64.zip")
  CHECKSUM_ARTIFACTS+=("${APP_NAME}_arm64.zip")
fi
if [[ -f "${APP_NAME}_x86_64" ]]; then
  zip -q -r "${APP_NAME}_x86_64.zip" "${APP_NAME}_x86_64"
  ARTIFACTS+=("${APP_NAME}_x86_64.zip")
  CHECKSUM_ARTIFACTS+=("${APP_NAME}_x86_64.zip")
fi
if [[ -d "${GUI_APP_NAME} ${VERSION}_arm64.app" ]]; then
  zip -q -r "Iconik_Locator_App_${VERSION_TAG}_arm64.zip" "${GUI_APP_NAME} ${VERSION}_arm64.app"
  ARTIFACTS+=("Iconik_Locator_App_${VERSION_TAG}_arm64.zip")
  CHECKSUM_ARTIFACTS+=("Iconik_Locator_App_${VERSION_TAG}_arm64.zip")
fi
if [[ -d "${GUI_APP_NAME} ${VERSION}_x86_64.app" ]]; then
  zip -q -r "Iconik_Locator_App_${VERSION_TAG}_x86_64.zip" "${GUI_APP_NAME} ${VERSION}_x86_64.app"
  ARTIFACTS+=("Iconik_Locator_App_${VERSION_TAG}_x86_64.zip")
  CHECKSUM_ARTIFACTS+=("Iconik_Locator_App_${VERSION_TAG}_x86_64.zip")
fi
shasum -a 256 "${CHECKSUM_ARTIFACTS[@]}" > checksums.txt
ARTIFACT_LIST=""
for artifact in "${ARTIFACTS[@]}"; do
  ARTIFACT_LIST+="  ${DIST}/${artifact}"$'\n'
done

msg "Artifacts ready in ${DIST}"
cat <<EOF
Artifacts:
${ARTIFACT_LIST}

If macOS marks a downloaded file as quarantined:
  xattr -dr com.apple.quarantine "${DIST}/${APP_NAME}_arm64"
  xattr -dr com.apple.quarantine "${DIST}/${APP_NAME}_x86_64"
EOF
