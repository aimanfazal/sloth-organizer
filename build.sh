#!/usr/bin/env bash
# build.sh — Build frontend and copy dist into the Python static folder
set -euo pipefail

echo "==> Installing frontend dependencies..."
cd frontend
npm install

echo "==> Building frontend..."
npm run build

cd ..

src="frontend/dist"
dest="backend/sloth_organizer/static"

echo "==> Syncing $src -> $dest ..."
rm -rf "$dest"
cp -r "$src" "$dest"

echo "==> Done."
