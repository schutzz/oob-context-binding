import socket
import time
import hashlib
import uuid
import os
import requests
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

def register_oob_context_webdis(webdis_url: str, key: str, traceparent: str, ttl: int = 5):
    """Pre-registers the Trace Context into Redis via Webdis REST API with TTL."""
    url = f"{webdis_url}/SET/oob:{key}/{traceparent}/EX/{ttl}"
    resp = requests.get(url, timeout=2)
    resp.raise_for_status()

def register_oob_context_redis(r_client, key: str, traceparent: str, ttl: int = 5):
    """Fallback: Pre-registers directly using Redis client."""
    r_client.setex(f"oob:{key}", ttl, traceparent)

def main():
    redis_host = os.environ.get("REDIS_HOST", "redis")
    webdis_host = os.environ.get("WEBDIS_HOST", "webdis")
    webdis_port = os.environ.get("WEBDIS_PORT", "7379")
    use_webdis = os.environ.get("USE_WEBDIS", "true").lower() == "true"

    webdis_url = f"http://{webdis_host}:{webdis_port}"
    r_client = None
    if not use_webdis:
        r_client = redis.Redis(host=redis_host, port=6379, db=0)

    src_ip = os.environ.get("SRC_IP", "10.0.1.10")
    dst_ip = os.environ.get("DST_IP", "10.0.1.20")
    dst_port = int(os.environ.get("DST_PORT", "20000"))
    function_code = int(os.environ.get("FUNCTION_CODE", "5"))  # DNP3 Direct Operate

    print(f"[SCADA-Emulator] Starting OOB Context Binding Sender (Target={dst_ip}:{dst_port})...", flush=True)
    time.sleep(3)  # Wait for services to initialize

    iteration = 0
    while True:
        iteration += 1
        traceparent = generate_w3c_traceparent()
        binding_key = compute_deterministic_key(src_ip, dst_ip, dst_port, function_code)

        # 1. Pre-register OOB Context
        try:
            if use_webdis:
                register_oob_context_webdis(webdis_url, binding_key, traceparent, ttl=5)
                print(f"[{iteration}] [SCADA-Sender] Pre-registered OOB Key via Webdis -> key={binding_key[:12]}..., traceparent={traceparent}", flush=True)
            else:
                register_oob_context_redis(r_client, binding_key, traceparent, ttl=5)
                print(f"[{iteration}] [SCADA-Sender] Pre-registered OOB Key via Redis -> key={binding_key[:12]}..., traceparent={traceparent}", flush=True)
        except Exception as e:
            print(f"[{iteration}] [SCADA-Sender] Error pre-registering OOB context: {e}", flush=True)

        # 2. Transmit UNMODIFIED Binary DNP3 Packet (Header: 0x05 0x64, FC: 0x05)
        dnp3_payload = bytes([0x05, 0x64, function_code, 0x0B, 0x00, 0x00, 0x00, 0x00])
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(dnp3_payload, (dst_ip, dst_port))
            print(f"[{iteration}] [SCADA-Sender] Sent binary DNP3 frame ({len(dnp3_payload)} bytes) to {dst_ip}:{dst_port}", flush=True)
        except Exception as e:
            print(f"[{iteration}] [SCADA-Sender] Error sending DNP3 packet: {e}", flush=True)

        time.sleep(2)

if __name__ == "__main__":
    main()
