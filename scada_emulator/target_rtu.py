import socket
import os

def main():
    listen_ip = os.environ.get("LISTEN_IP", "0.0.0.0")
    listen_port = int(os.environ.get("LISTEN_PORT", "20000"))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((listen_ip, listen_port))

    print(f"[RTU-Outstation] Mock DNP3 RTU Server listening on UDP {listen_ip}:{listen_port}...", flush=True)

    while True:
        data, addr = sock.recvfrom(1024)
        if len(data) >= 3 and data[0] == 0x05 and data[1] == 0x64:
            function_code = data[2]
            print(f"[RTU-Outstation] Received DNP3 Packet from {addr[0]}:{addr[1]} | FC=0x{function_code:02x} | Length={len(data)} bytes", flush=True)
            if function_code == 0x05:
                print(f"[RTU-Outstation] ⚡ Direct Operate Executed: Breaker Opened!", flush=True)

if __name__ == "__main__":
    main()
