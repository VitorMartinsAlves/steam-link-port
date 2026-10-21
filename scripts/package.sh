#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/dist/steam-link-roku.zip"

mkdir -p "${ROOT}/dist"
rm -f "${OUT}"
cd "${ROOT}"
zip -r "${OUT}" manifest source components
printf 'Created %s\n' "${OUT}"
