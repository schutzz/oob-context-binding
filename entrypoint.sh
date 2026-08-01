#!/bin/bash
set -e

if [ ! -f "vmlinux.h" ]; then
    echo "=== Generating vmlinux.h from host kernel BTF ==="
    bpftool btf dump file /sys/kernel/btf/vmlinux format c > vmlinux.h
fi

echo "=== Building eBPF program and loader ==="
make

exec "$@"
