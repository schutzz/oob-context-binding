# Deterministic Out-of-Band (OOB) Context Binding

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-green.svg)](https://www.docker.com/)

A lightweight reference implementation of **Deterministic Out-of-Band (OOB) Context Binding** for legacy OT/ICS protocols (e.g., DNP3, Modbus TCP, IEC 61850).

This mechanism solves the fundamental visibility gap in Industrial Control Systems: **enabling end-to-end W3C Trace Context (OpenTelemetry) correlation across IT/OT boundaries without modifying binary OT network packets or violating protocol specifications.**

---

## 🎯 The Problem: Why Legacy OT Protocols Lack Distributed Tracing

In modern IT environments, W3C Trace Context headers (such as `traceparent`) are injected directly into HTTP/gRPC headers to trace requests across microservices.

However, in Industrial Control Systems (ICS / SCADA):
1. **No Header Fields**: Protocols like DNP3, Modbus TCP, and IEC 61850 GOOSE have rigid binary structures without extensible key-value header fields.
2. **Strict Payload Specifications**: Mutating packet payloads breaks CRC/checksum verification and causes legacy Remote Terminal Units (RTUs) or IEDs to reject packets as malformed.
3. **Loss of Causality**: When an IT/HMI system issues a command, passive network monitoring tools (like Zeek or Snort) see raw packets but cannot correlate them to the originating IT user session or APM trace ID.

---

## 💡 The Solution: Deterministic OOB Context Binding

Instead of mutating the binary protocol, **Deterministic OOB Context Binding** decouples context propagation into an Out-of-Band (OOB) control plane using a deterministic hash key lookup:

```
[ IT / HMI Application ] 
       │
       ├─────── 1. Pre-registers W3C Trace Context via OOB API ───────► [ OOB KV Store (Redis) ]
       │        Key: SHA256(src_ip, dst_ip, dst_port, function_code)           │
       │        TTL: Short-lived (e.g., 5 seconds)                             │
       │                                                                       │ 3. Key Match &
       └─────── 2. Sends Unmodified Binary OT Packet (DNP3/Modbus) ──┐         │    Context Retrieval
                                                                     ▼         ▼
                                                           [ Passive OT Sensor / DPI ]
                                                                     │
                                                                     ▼ 4. Emits Enriched OTLP Span
                                                           [ OpenTelemetry / APM ]
```

### Protocol Workflow
1. **Pre-Registration (IT/HMI Side)**:
   Before sending a binary OT command, the client generates a **Deterministic Binding Key** based on shared session attributes (e.g., `SHA256(src_ip + dst_ip + dst_port + function_code)`). It pre-registers the active W3C `traceparent` (Trace ID + Span ID) in an Out-of-Band Key-Value Store (Redis) with a short Time-To-Live (TTL).
2. **In-Band Transmission**:
   The client transmits the **original, unmodified binary OT packet** over the network.
3. **Passive Sniffing & Key Recomputation (Sensor Side)**:
   A passive network sensor (e.g., Zeek or Python Sidecar) captures the raw binary frame, parses the layer 4/7 attributes, recomputes the exact same **Deterministic Binding Key**, and queries the OOB Key-Value Store.
4. **Context Stitching**:
   Upon a cache hit, the sensor retrieves the original W3C Trace Context and attaches it to the generated security event/log. The resulting OTLP span seamlessly stitches the IT trigger to the OT physical action.

---

## 📁 Repository Structure

```
oob-context-binding/
├── docker-compose.yml        # Orchestrates Redis, Sender, Sensor, and Target
├── README.md                 # Project Documentation
├── LICENSE                   # MIT License
├── src/
│   ├── sender.py             # Pre-registers Trace Context and sends DNP3 command
│   ├── sensor.py             # Passive packet sniffer & OOB context enricher
│   └── target_rtu.py         # Mock DNP3 Outstation / RTU server
```

---

## 🚀 Quickstart

### Prerequisites
* Docker & Docker Compose V2

### Running the Demo

1. Clone the repository:
   ```bash
   git clone https://github.com/schutzz/oob-context-binding.git
   cd oob-context-binding
   ```

2. Start the environment:
   ```bash
   docker compose up --build
   ```

3. Observe the output:
   * **`sender`** generates a random W3C `traceparent`, pre-registers it in Redis using `sha256("10.0.1.10:10.0.1.20:20000:fc05")`, and sends a DNP3 `Direct Operate` packet.
   * **`sensor`** passively captures the packet, computes the same SHA256 key, queries Redis, and prints the **Enriched Trace Log** showing the successfully stitched W3C Trace ID!

---

## 🔑 Key Deterministic Binding Key Formats

Depending on protocol semantics, binding keys can be formatted as:

| Protocol | Binding Key Components | Formula |
| :--- | :--- | :--- |
| **DNP3** | `src_ip`, `dst_ip`, `dst_port`, `function_code` | `SHA256(src_ip \| dst_ip \| dst_port \| fc)` |
| **Modbus TCP** | `src_ip`, `dst_ip`, `unit_id`, `function_code`, `register_addr` | `SHA256(src_ip \| dst_ip \| unit_id \| fc \| addr)` |
| **IEC 61850 GOOSE** | `src_mac`, `dst_mac`, `gocbRef`, `stNum` | `SHA256(gocbRef \| stNum)` |

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
