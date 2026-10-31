#!/bin/sh
set -eu

echo "project: $(pwd)"
echo "node: $(command -v node || true)"
node -v
echo "npm: $(command -v npm || true)"
npm -v
echo "npx: $(command -v npx || true)"
npx -v
echo "uni:"
node node_modules/@dcloudio/vite-plugin-uni/bin/uni.js --version

test -f index.html
test -f pages.json
test -f manifest.json
test -f package.json
test -x node_modules/.bin/uni

echo "HBuilderX frontend environment OK"
