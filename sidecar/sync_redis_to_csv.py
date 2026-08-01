import time
import os
import requests
import json

def fetch_keys_webdis(webdis_url: str):
    """Fetches all active OOB binding keys from Redis via Webdis."""
    resp = requests.get(f"{webdis_url}/KEYS/oob:*", timeout=2)
    resp.raise_for_status()
    data = resp.json()
    return data.get("KEYS", [])

def fetch_val_webdis(webdis_url: str, key: str):
    """Fetches W3C traceparent value for a key via Webdis."""
    resp = requests.get(f"{webdis_url}/GET/{key}", timeout=2)
    resp.raise_for_status()
    data = resp.json()
    return data.get("GET")

def main():
    webdis_host = os.environ.get("WEBDIS_HOST", "webdis")
    webdis_port = os.environ.get("WEBDIS_PORT", "7379")
    vector_api_url = os.environ.get("VECTOR_API_URL", "http://vector:8686")
    csv_path = os.environ.get("CSV_PATH", "/data/webdis_cache.csv")
    poll_interval = float(os.environ.get("POLL_INTERVAL", "1.0"))

    webdis_url = f"http://{webdis_host}:{webdis_port}"
    print(f"[Sidecar] Starting Redis-to-CSV Sync Sidecar (Webdis={webdis_url}, CSV={csv_path})...", flush=True)

    # Ensure output dir exists
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    while True:
        try:
            keys = fetch_keys_webdis(webdis_url)
            rows = []
            for k in keys:
                val = fetch_val_webdis(webdis_url, k)
                if val:
                    clean_key = k.replace("oob:", "")
                    rows.append(f"{clean_key},{val}")

            # Write to temp file first for atomic replacement
            tmp_path = f"{csv_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("binding_key,traceparent\n")
                for r in rows:
                    f.write(f"{r}\n")

            # Atomic replace
            os.replace(tmp_path, csv_path)

            # Trigger Vector enrichment table reload
            try:
                reload_url = f"{vector_api_url}/enrichment_tables/webdis_table/reload"
                requests.post(reload_url, timeout=1)
            except Exception:
                # Vector API might not be available yet or enrichment reloading endpoint not configured
                pass

        except Exception as e:
            # Print error if webdis is down or resetting
            pass

        time.sleep(poll_interval)

if __name__ == "__main__":
    main()
