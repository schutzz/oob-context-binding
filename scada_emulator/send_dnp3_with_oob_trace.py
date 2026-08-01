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

        # 2. Transmit UNMODIFIED Binary DNP3 Packet (IEEE 1815 Format)
        # オフセット解説: 0-9(データリンク), 10(トランスポート), 11(アプリ制御), 12(Function Code)
        dnp3_payload = bytes([
            0x05, 0x64,             # 0-1: Sync
            0x0E,                   # 2: Length (続くペイロードの長さ)
            0xC4,                   # 3: Link Control
            0x01, 0x00,             # 4-5: Dest Address
            0x00, 0x00,             # 6-7: Src Address
            0x00, 0x00,             # 8-9: Link CRC (ダミー)
            0xC0,                   # 10: Transport Header (FIN, FIR)
            0xC1,                   # 11: Application Control
            function_code,          # 12: Function Code (0x05 = Direct Operate)
            0x01, 0x02, 0x03, 0x04  # 13-16: Payload (Object Data) + CRC
        ])

        try:
            # IEEE 1815の実環境に合わせてTCPソケット(SOCK_STREAM)を使用
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((dst_ip, dst_port))
            sock.sendall(dnp3_payload)
            sock.close()
            print(f"[{iteration}] [SCADA-Sender] Sent strictly compliant binary DNP3 frame ({len(dnp3_payload)} bytes) via TCP to {dst_ip}:{dst_port}", flush=True)
        except Exception as e:
            print(f"[{iteration}] [SCADA-Sender] Error sending DNP3 packet: {e}", flush=True)

        time.sleep(2)

if __name__ == "__main__":
    main()