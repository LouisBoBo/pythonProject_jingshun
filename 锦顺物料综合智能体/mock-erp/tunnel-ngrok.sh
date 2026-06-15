#!/usr/bin/env bash
# 将本地 Mock ERP (8900) 暴露给远程 Dify 服务器
# 用法：先 ./run.sh，再本脚本；或 ./tunnel-ngrok.sh --with-mock
set -euo pipefail
cd "$(dirname "$0")"

PORT="${MOCK_ERP_PORT:-8900}"
NGROK_DOMAIN="${NGROK_DOMAIN:-}"

start_mock() {
  if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    echo "[mock] 已在运行 http://127.0.0.1:${PORT}"
    return
  fi
  echo "[mock] 启动 Mock ERP ..."
  nohup bash run.sh >/tmp/mock-erp.log 2>&1 &
  for _ in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
      echo "[mock] 就绪"
      return
    fi
    sleep 0.5
  done
  echo "[mock] 启动超时，查看 /tmp/mock-erp.log"
  exit 1
}

if [[ "${1:-}" == "--with-mock" ]]; then
  start_mock
fi

if ! curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
  echo "Mock ERP 未运行。请先执行: ./run.sh"
  echo "或: ./tunnel-ngrok.sh --with-mock"
  exit 1
fi

if ! command -v ngrok >/dev/null 2>&1; then
  echo "未找到 ngrok。安装: https://ngrok.com/download"
  exit 1
fi

echo ""
echo "=========================================="
echo "  ngrok 穿透 Mock ERP → 远程 Dify"
echo "=========================================="
echo ""
echo "本地 Mock: http://127.0.0.1:${PORT}"
echo "ngrok 控制台: http://127.0.0.1:4040"
echo ""
echo "启动后请复制 Forwarding 的 https 地址，Dify 配置："
echo "  ERP_BASE_URL = https://<你的子域>.ngrok-free.app/api"
echo ""
echo "注意："
echo "  1. ngrok 免费版可能拦截 API，Dify Tool 需加 Header："
echo "     ngrok-skip-browser-warning: true"
echo "  2. 隧道地址每次重启会变（未绑固定域名时）"
echo "  3. 保持本终端不关，关则 Dify 无法访问 Mock"
echo ""

if [[ -n "$NGROK_DOMAIN" ]]; then
  exec ngrok http "$PORT" --domain="$NGROK_DOMAIN"
else
  exec ngrok http "$PORT"
fi
