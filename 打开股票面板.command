#!/bin/zsh
cd "$(dirname "$0")" || exit 1

URL="http://localhost:5173/"
LOG_FILE="$PWD/stock-dashboard.log"

export PATH="/Users/fan/.hermes/node/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

NODE_BIN="$(command -v node)"
if [ -z "$NODE_BIN" ]; then
  echo "没有找到 Node.js，无法启动股票面板。" | tee -a "$LOG_FILE"
  echo "请把这个窗口截图发给我。" | tee -a "$LOG_FILE"
  read -k 1 "?按任意键关闭..."
  exit 1
fi

if lsof -iTCP:5173 -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "股票面板已经在运行。"
  open "$URL"
  echo "已打开：$URL"
  echo "可以关闭这个窗口。"
  read -k 1 "?按任意键关闭..."
  exit 0
fi

echo "正在启动股票面板..."
echo "启动时间：$(date)" >> "$LOG_FILE"
"$NODE_BIN" server.js >> "$LOG_FILE" 2>&1 &
SERVER_PID=$!

for i in {1..20}; do
  if lsof -iTCP:5173 -sTCP:LISTEN -n -P >/dev/null 2>&1; then
    open "$URL"
    echo "已打开：$URL"
    echo "保持这个窗口打开，网页服务才会持续运行。"
    echo "要停止网页服务，请关闭这个窗口，或按 Control+C。"
    wait "$SERVER_PID"
    exit 0
  fi
  if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    echo "启动失败。最近日志：" | tee -a "$LOG_FILE"
    tail -n 20 "$LOG_FILE"
    echo "请把这个窗口截图发给我。" | tee -a "$LOG_FILE"
    read -k 1 "?按任意键关闭..."
    exit 1
  fi
  sleep 0.5
done

echo "启动超时。最近日志：" | tee -a "$LOG_FILE"
tail -n 20 "$LOG_FILE"
echo "请把这个窗口截图发给我。" | tee -a "$LOG_FILE"
read -k 1 "?按任意键关闭..."
exit 1
