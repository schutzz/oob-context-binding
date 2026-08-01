import socket
import sys

def main():
    host = '0.0.0.0'
    port = 20000
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"[RTU] Mock DNP3 Outstation listening on UDP {host}:{port}...", flush=True)

    while True:
        data, addr = sock.recvfrom(1024)
        print(f"[RTU] Received {len(data)} bytes from {addr[0]}:{addr[1]}", flush=True)
        if len(data) >= 4 and data[0] == 0x05 and data[1] == 0x64:
            fc = data[2]
            print(f"[RTU] Valid DNP3 Header! Magic=(0x05, 0x64), FunctionCode=0x{fc:02x}", flush=True)

if __name__ == "__main__":
    main()
