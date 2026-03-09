#!/bin/bash
# このスクリプトがあるフォルダで HTTP サーバーを起動する
cd "$(dirname "$0")"
PORT=8765
echo "=========================================="
echo "  JLPT N5 ローマ字タイピング練習"
echo "=========================================="
echo ""
echo "  起動先: $(pwd)"
echo "  開くURL: http://localhost:${PORT}"
echo ""
echo "  ブラウザで上記URLを開いてください。"
echo "  Ctrl+C でサーバーを停止します。"
echo "=========================================="
exec python3 -m http.server "$PORT"
