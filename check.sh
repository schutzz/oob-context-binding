#!/bin/bash
echo "=== 1. vmlinux.h の存在確認 ==="
if [ -f "vmlinux.h" ]; then
    echo "[OK] vmlinux.h は存在します（サイズ: $(ls -l vmlinux.h | awk '{print $5}') bytes）"
else
    echo "[NG] vmlinux.h が存在しません"
fi

echo -e "\n=== 2. カーネルBTF (/sys/kernel/btf/vmlinux) の存在確認 ==="
if [ -f "/sys/kernel/btf/vmlinux" ]; then
    echo "[OK] カーネルBTFが存在します"
else
    echo "[NG] カーネルBTFが存在しません（コンテナの特権モード不足や古いカーネルの可能性）"
fi

echo -e "\n=== 3. bpftool コマンドの有無確認 ==="
if command -v bpftool &> /dev/null; then
    echo "[OK] bpftool はインストールされています"
else
    echo "[NG] bpftool がインストールされていません"
fi

echo -e "\n=== 4. libbpf ヘッダーの存在確認 ==="
if [ -d "/usr/include/bpf" ]; then
    echo "[OK] /usr/include/bpf ディレクトリが存在します"
else
    echo "[NG] libbpf-dev が未導入の可能性があります"
fi
