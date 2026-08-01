# Deterministic Out-of-Band (OOB) Context Binding

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI Status](https://github.com/schutzz/oob-context-binding/actions/workflows/ebpf-full-ci.yml/badge.svg)](https://github.com/schutzz/oob-context-binding/actions/workflows/ebpf-full-ci.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-green.svg)](https://www.docker.com/)
[![Vector](https://img.shields.io/badge/Vector-0.34-blueviolet.svg)](https://vector.dev/)
[![Zenodo](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.21731823-blue.svg)](https://doi.org/10.5281/zenodo.21731823)

A production-grade reference implementation of **Deterministic Out-of-Band (OOB) Context Binding** for legacy OT/ICS protocols (e.g., DNP3, Modbus TCP, IEC 61850).

📄 **Whitepaper / Preprint**: [Read on Zenodo](https://zenodo.org/records/21731823) | **DOI**: [`10.5281/zenodo.21731823`](https://doi.org/10.5281/zenodo.21731823)

This mechanism solves the fundamental visibility gap in Industrial Control Systems: **enabling end-to-end W3C Trace Context (OpenTelemetry) correlation across IT/OT boundaries without modifying binary OT network packets or violating protocol specifications.**

---

## The Problem: Why Legacy OT Protocols Lack Distributed Tracing

In modern IT environments, W3C Trace Context headers (such as `traceparent`) are injected directly into HTTP/gRPC headers to trace requests across microservices.

However, in Industrial Control Systems (ICS / SCADA):
1. **No Header Fields**: Protocols like DNP3 (IEEE 1815), Modbus TCP, and IEC 61850 GOOSE have rigid binary structures without extensible key-value header fields.
2. **Strict Payload Specifications**: Mutating packet payloads breaks CRC/checksum verification and causes legacy Remote Terminal Units (RTUs) or IEDs to reject packets as malformed or drop connections.
3. **Loss of Causality**: When an IT/HMI system issues a command, passive network monitoring tools see raw packets but cannot correlate them to the originating IT user session or APM trace ID.

---

## The Solution: Deterministic OOB Context Binding

Instead of mutating the binary protocol, **Deterministic OOB Context Binding** decouples context propagation into an Out-of-Band (OOB) control plane using a deterministic hash key lookup:

```
[ IT / HMI Application (SCADA) ] 
       │
       ├─────── 1. Pre-registers W3C Trace Context via Webdis REST API ──► [ OOB KV Store (Redis/Webdis) ]
       │        Key: SHA256(src_ip + dst_ip + dst_port + function_code)            │
       │        TTL: Short-lived (5 seconds)                                       │ 3. Non-blocking Atomic
       │                                                                           │    CSV Sync & Reload
       └─────── 2. Sends Unmodified Binary OT Packet (DNP3/Modbus) ──┐             ▼
                                                                      │    [ Python Sidecar ] ──► [ Vector Router ]
                                                                      ▼            │                     │
                                                            [ Passive Sensor / TAP ]                     │ 4. Emits Enriched
                                                                      │                                  ▼    Fat Spans
                                                                      └────────────────────────► [ OpenTelemetry / SOC ]
```

### Key Innovations
1. **Zero Payload Overhead (0.0% In-Band Mutation)**: Leaves raw DNP3/Modbus binary frames untouched. Guaranteed compatibility with legacy RTUs.
2. **Stateless Stream Processing & OOM Safety**: Vector log router remains completely stateless. The Python Sidecar atomically syncs Redis keys into an in-memory CSV lookup table (`webdis_cache.csv`) and triggers Vector's `/enrichment_tables/webdis_table/reload` API without blocking the streaming engine.
3. **Fat Spans for Security AI & SOC Analysis**: Encapsulates raw Zeek logs, DNP3 function codes, network IPs, and pipeline processing delays (`processing_delay_ms`) as OTLP span attributes for automated AI threat hunting.

---

## Repository Structure

```
oob-context-binding/
├── docker-compose.yml              # Orchestrates Redis, Webdis, Vector, Sidecar, and SCADA Emulator
├── README.md                       # Project Documentation
├── LICENSE                         # MIT License
├── scada_emulator/
│   ├── send_dnp3_with_oob_trace.py # SCADA client: Pre-registers W3C trace & sends raw DNP3 frame
│   └── target_rtu.py               # Mock DNP3 Outstation / RTU server
├── sidecar/
│   └── sync_redis_to_csv.py        # Async sidecar: Syncs Webdis keys to CSV & reloads Vector table
├── vector_config/
│   ├── vector.toml                 # Vector VRL pipeline configuration for OOB context stitching
│   └── webdis_cache.csv            # Shared CSV lookup table
└── docs/
    └── evaluation.md               # Quantitative benchmarking results & latency breakdowns
```

---

## Quickstart

### Prerequisites
* Docker & Docker Compose V2
* **(For eBPF Vanguard Mode)**: A native Linux host or Windows WSL2 with `/sys/kernel/btf/vmlinux`. 
  * *Note: Running the full eBPF pipeline on Docker Desktop for Windows is now fully supported! By extracting the native BTF file from your WSL2 kernel and mounting it to the container, our custom CO-RE loader bypasses virtualized kernel constraints via the `CUSTOM_BTF_PATH` environment variable.*

### Running the Demo

1. Clone the repository:
   ```bash
   git clone https://github.com/schutzz/oob-context-binding.git
   cd oob-context-binding
   ```

2. Launch the pipeline:
   ```bash
   docker compose up --build
   ```

3. Observe the output:
   * **`scada_sender`**: Generates active W3C `traceparent` (`00-{trace_id}-{span_id}-01`), pre-registers it in Redis via Webdis with `sha256("10.0.1.10:10.0.1.20:20000:5")`, and sends an unmodified DNP3 `Direct Operate` packet.
   * **`sidecar`**: Synchronizes the key to `webdis_cache.csv` and signals Vector.
   * **`vector`**: Receives the packet log, computes the matching SHA256 key in VRL, stitches the `traceparent`, and outputs the enriched `Fat Span`!

---

## Quantitative Benchmarks

See [docs/evaluation.md](docs/evaluation.md) for full benchmarking details.

| Metric | Measured Value | Standard Target | Status |
| :--- | :--- | :--- | :--- |
| **In-Band Overhead** | **0.0%** (0 bytes added) | 0 bytes | PERFECT |
| **Trace Stitching Rate** | **100.0%** (up to 5,000 pps) | >99.9% | PASS |
| **Pipeline Latency** | **~0.41 ms** | <1.0 ms | PASS |
| **OOM Resilience** | **Stateless / No Memory Leak** | Zero OOM | PASS |

---

## Automated CI/CD (GitHub Actions)

This repository includes a fully automated CI/CD pipeline using **GitHub Actions** (`.github/workflows/ebpf-full-ci.yml`) to guarantee the reproducibility of the research results.

Anyone can easily reproduce the eBPF Vanguard Mode benchmarks without preparing a complex native Linux environment. **Just fork this repository**, and GitHub Actions will automatically spin up an Ubuntu 22.04 runner and execute the tests on every push!

### What the CI Pipeline Asserts:
1. **eBPF Compilation**: Compiles the XDP program from scratch using `clang` and a standalone `bpftool`.
2. **Full Pipeline Boot**: Starts Redis, Vector, Sidecar, and the eBPF module via `docker compose up --build` with all necessary kernel capabilities (`privileged: true`, `/sys/kernel/btf`).
3. **High-Speed Stress Test**: Fires continuous DNP3 packets to rigorously test the stream processing engine.
4. **Zero Overhead & 100% Success Guarantee**: The test script automatically asserts that the OOB context stitching succeeded perfectly (`Success Rate: 100%`) and that the DNP3 payload was never modified (`Overhead: 0 bytes`). The CI build is strictly configured to **fail** if these conditions are not met.

---

## Research & Citation

If you use this project or architecture in your academic work, please cite our whitepaper/dataset:

```bibtex
@misc{oob_context_binding_2027,
  author       = {Daichi Terayama (schutzz)},
  title        = {Unbreaking the Kill Chain: OOB Deterministic Binding for Legacy OT Protocols},
  year         = 2026,
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.21731823},
  url          = {https://github.com/schutzz/oob-context-binding}
}
```

## License

This project is licensed under the [MIT License](LICENSE).
