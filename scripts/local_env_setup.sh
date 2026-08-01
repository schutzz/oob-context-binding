#!/bin/bash
# local_env_setup.sh
# eBPF Cyber Range: Vagrant 仮想マシン内での一発起動スクリプト

set -e

echo "==========================================="
echo " OOB Context Binding - eBPF Cyber Range"
echo "==========================================="

# プロジェクトルート（/vagrant）へ移動
if [ -d "/vagrant" ]; then
    cd /vagrant
else
    echo "ERROR: /vagrant directory not found. Are you running this inside the Vagrant VM?"
    exit 1
fi

echo "[*] Checking BTF (BPF Type Format) support..."
if [ ! -f "/sys/kernel/btf/vmlinux" ]; then
    echo "[!] ERROR: BTF file not found at /sys/kernel/btf/vmlinux."
    echo "[!] eBPF Vanguard Mode cannot run without kernel BTF support."
    exit 1
fi
echo "[-] BTF support confirmed."

echo "[*] Cleaning up old containers..."
docker compose down -v || true

echo "[*] Starting the OOB Pipeline (eBPF Vanguard + Zeek/Vector)..."
docker compose up -d --build

echo "[*] Waiting for services to initialize..."
sleep 10
docker compose ps

echo "==========================================="
echo " Environment is up and running!"
echo " To run the benchmark test, execute:"
echo "   docker compose exec scada_sender python /app/scada_emulator/send_dnp3_with_oob_trace.py"
echo "==========================================="
