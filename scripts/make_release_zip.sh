#!/usr/bin/env bash
# Creates a shareable zip of the project from Git (R1).
#
# `git archive` only includes COMMITTED, tracked files, so .env, db.sqlite3, media/,
# logs/, .idea/ and the ChromaDB data can never end up in the zip by accident.
# Commit your changes first; uncommitted work is not included.
#
# Usage: scripts/make_release_zip.sh [git-ref]   (default: HEAD)
set -euo pipefail

REF="${1:-HEAD}"
cd "$(git rev-parse --show-toplevel)"
NAME="genai-chat-django-$(git rev-parse --short "$REF")"
mkdir -p dist-release
git archive --format=zip --prefix="${NAME}/" -o "dist-release/${NAME}.zip" "$REF"
echo "Created dist-release/${NAME}.zip"
