#!/usr/bin/env bash
# Build frontendu na Vercelu. Dopóki nie ma frontend/ — strona zastępcza.
set -euo pipefail

if [ -f frontend/package.json ]; then
  npm --prefix frontend ci
  npm --prefix frontend run build
else
  mkdir -p frontend/dist
  cat > frontend/dist/index.html <<'EOF'
<!doctype html>
<html lang="pl">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sztafeta Słów</title>
<h1>Sztafeta Słów</h1>
<p>Frontend w budowie — <a href="/api/health">/api/health</a></p>
</html>
EOF
fi
