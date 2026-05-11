      
#!/bin/sh

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "未找到 python3/python"
  exit 1
fi

if [ "$1" = "start" ]; then
  shift
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/shell_plugin.py" "$@"

    