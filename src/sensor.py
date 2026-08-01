import socket
import hashlib
import os
import sys
import redis
from scapy.all import sniff, UDP, IP

def compute_deterministic_key(src_ip: str, dst_ip: str, dst_port: int, function_code: int) -> str:
    """Computes the exact same deterministic binding hash from captured packet attributes."""
    raw_str = f"{src_ip}:{dst_ip}:{dst_port}:{function_code}"
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

class OOBSensorEnricher:
    def __init__(self, redis_host="127.0.0.1", redis_port=6379):
        self.r = redis.Redis(host=redis_host, port=redis_port, db=0)

    def packet_callback(self, pkt):
        if pkt.haslayer(UDP) and pkt.haslayer(IP):
            ip_layer = pkt[IP]
            udp_layer = pkt[UDP]
            payload = bytes(udp_layer.payload)

            # Check for DNP3 Header (Magic Bytes: 0x05 0x64)
            if len(payload) >= 3 and payload[0] == 0x05 and payload[1] == 0x64:
                function_code = payload[2]
                src_ip = ip_layer.src
                dst_ip = ip_layer.dst
                dst_port = udp_layer.dport

                # Recompute Deterministic Key
                binding_key = compute_deterministic_key(src_ip, dst_ip, dst_port, function_code)

                # Query OOB Key-Value Store
                cached_trace = self.r.get(f"oob_context:{binding_key}")

                print("=" * 70, flush=True)
                print(f"[OT-Sensor] Captured Raw DNP3 Packet: {src_ip}:{udp_layer.sport} -> {dst_ip}:{dst_port}", flush=True)
                print(f"[OT-Sensor] Parsed Protocol Attribute: FunctionCode = 0x{function_code:02x}", flush=True)
                print(f"[OT-Sensor] Recomputed Deterministic Key: {binding_key[:16]}...", flush=True)

                if cached_trace:
                    traceparent = cached_trace.decode('utf-8')
                    print(f"[OT-Sensor] ✅ OOB CONTEXT BINDING HIT!", flush=True)
                    print(f"[OT-Sensor] 🔗 Stitched W3C Traceparent: {traceparent}", flush=True)
                    print(f"[OT-Sensor] 🟢 Emitted OTLP Event: {{'event': 'DNP3_DIRECT_OPERATE', 'src': '{src_ip}', 'dst': '{dst_ip}', 'traceparent': '{traceparent}'}}", flush=True)
                else:
                    print(f"[OT-Sensor] ⚠️ OOB CONTEXT MISS! (No matching pre-registration found)", flush=True)
                print("=" * 70, flush=True)

def main():
    redis_host = os.environ.get("REDIS_HOST", "127.0.0.1")
    enricher = OOBSensorEnricher(redis_host=redis_host)
    print(f"[OT-Sensor] Passive Sniffer initialized. Monitoring DNP3 traffic (UDP 20000)...", flush=True)
    sniff(filter="udp port 20000", prn=enricher.packet_callback, store=0)

if __name__ == "__main__":
    main()
