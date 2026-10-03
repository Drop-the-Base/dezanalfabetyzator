#!/usr/bin/env bash
# Build frontendu na Vercelu. Dopóki nie ma frontend/ — strona zastępcza.
# Upewnij się, że uv jest w PATH dla Vercel Python builder
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found in PATH, attempting to install..."
  curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null || true
  if [ -f "$HOME/.local/bin/uv" ]; then
    sudo cp "$HOME/.local/bin/uv" /usr/local/bin/uv 2>/dev/null || cp "$HOME/.local/bin/uv" /usr/local/bin/uv 2>/dev/null || true
  fi
fi

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
