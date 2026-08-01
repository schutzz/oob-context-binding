import socket
import time
import hashlib
import uuid
import os
import redis

def compute_deterministic_key(src_ip: str, dst_ip: str, dst_port: int, function_code: int) -> str:
    """Computes a deterministic binding hash from shared network & protocol attributes."""
    raw_str = f"{src_ip}:{dst_ip}:{dst_port}:{function_code}"
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

def generate_w3c_traceparent() -> str:
    """Generates a standard W3C Trace Context string (traceparent)."""
    trace_id = uuid.uuid4().hex
    parent_id = uuid.uuid4().hex[:16]
    return f"00-{trace_id}-{parent_id}-01"

def main():
    redis_host = os.environ.get("REDIS_HOST", "redis")
    r = redis.Redis(host=redis_host, port=6379, db=0)

    src_ip = "10.0.1.10"
    dst_ip = "10.0.1.20"
    dst_port = 20000
    function_code = 0x05  # DNP3 Direct Operate

    print("[IT-Sender] Initializing Deterministic OOB Context Binding Demo...", flush=True)
    time.sleep(3)  # Wait for services to settle

    for iteration in range(1, 6):
        # 1. Generate active W3C Trace Context
        traceparent = generate_w3c_traceparent()
        print(f"\n[IT-Sender] Step 1: Active W3C Traceparent Generated -> {traceparent}", flush=True)

        # 2. Compute Deterministic Key & Pre-register to Redis OOB Store
        binding_key = compute_deterministic_key(src_ip, dst_ip, dst_port, function_code)
        r.setex(f"oob_context:{binding_key}", 5, traceparent)  # 5-second TTL
        print(f"[IT-Sender] Step 2: Pre-registered OOB Key [sha256({src_ip}:{dst_ip}:{dst_port}:{function_code})] -> Redis (TTL=5s)", flush=True)

        # 3. Transmit UNMODIFIED Binary DNP3 Packet (Header: 0x05 0x64, FC: 0x05)
        dnp3_payload = bytes([0x05, 0x64, function_code, 0x0B, 0x00, 0x00, 0x00, 0x00])
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(dnp3_payload, (dst_ip, dst_port))
        print(f"[IT-Sender] Step 3: Sent Unmodified DNP3 Binary Frame ({len(dnp3_payload)} bytes) to {dst_ip}:{dst_port}", flush=True)

        time.sleep(4)

if __name__ == "__main__":
    main()
