#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_APP="${ROOT}/dist/steam-link-roku.zip"
OUT_COMPANION="${ROOT}/dist/steam-link-roku-companion.zip"

mkdir -p "${ROOT}/dist"
rm -f "${OUT_APP}" "${OUT_COMPANION}"
cd "${ROOT}"
zip -r "${OUT_APP}" manifest source components
cd "${ROOT}/companion"
zip -r "${OUT_COMPANION}" bridge.py README.md
printf 'Created %s\nCreated %s\n' "${OUT_APP}" "${OUT_COMPANION}"
