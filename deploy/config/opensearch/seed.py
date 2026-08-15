#!/usr/bin/env python3
"""Seed Design 3 OpenSearch so Dashboards Discover is not empty.

Copies live Weaviate runbook chunks (k-NN vectors) and sample service logs,
then creates OpenSearch Dashboards index patterns.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OS_URL = os.environ.get("OPENSEARCH_URL", "http://localhost:9201").rstrip("/")
OSD_URL = os.environ.get("DASHBOARDS_URL", "http://localhost:5602").rstrip("/")
WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://localhost:8088").rstrip("/")
LOGS_DIR = Path(os.environ.get("LOGS_DIR", "/logs"))
RUNBOOKS_DIR = Path(os.environ.get("RUNBOOKS_DIR", "/runbooks"))
RUNBOOKS_INDEX = "agentops-d3-runbooks"
LOGS_INDEX = "agentops-d3-logs"


def req(url, method="GET", body=None, headers=None, timeout=20):
    data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw.decode()) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw.decode()) if raw else {}
        except Exception:
            parsed = {"error": raw.decode("utf-8", "replace")}
        return exc.code, parsed
    except urllib.error.URLError as exc:
        return 0, {"error": str(exc.reason)}


def wait(url, ok=lambda s, b: 200 <= s < 300, tries=40, delay=3, label="service"):
    for i in range(tries):
        status, body = req(url)
        if ok(status, body):
            print(f"{label} ready ({status})")
            return True
        print(f"waiting for {label} ({i + 1}/{tries}) status={status}")
        time.sleep(delay)
    raise SystemExit(f"{label} did not become ready: {url}")


def put_index(name, body):
    status, resp = req(f"{OS_URL}/{name}", method="PUT", body=body)
    if status in (200, 201):
        print(f"created index {name}")
        return True
    if status == 400 and "already" in json.dumps(resp).lower():
        print(f"index {name} already exists")
        return True
    print(f"create {name} failed {status}: {resp}")
    return False


def delete_index(name):
    req(f"{OS_URL}/{name}", method="DELETE")


def bulk(index, docs):
    if not docs:
        return 0
    lines = []
    for doc in docs:
        _id = doc.pop("_id", None)
        action = {"index": {"_index": index}}
        if _id:
            action["index"]["_id"] = _id
        lines.append(json.dumps(action))
        lines.append(json.dumps(doc))
    payload = ("\n".join(lines) + "\n").encode()
    r = urllib.request.Request(
        f"{OS_URL}/_bulk",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-ndjson"},
    )
    with urllib.request.urlopen(r, timeout=60) as resp:
        result = json.loads(resp.read().decode())
    if result.get("errors"):
        first = next((i for i in result.get("items", []) if i.get("index", {}).get("error")), None)
        print(f"bulk errors on {index}: {first}")
    return len(docs)


def fetch_weaviate():
    items = []
    offset = 0
    while True:
        status, data = req(f"{WEAVIATE_URL}/v1/objects?class=Runbook&limit=50&offset={offset}&include=vector")
        if status != 200:
            print(f"weaviate fetch failed {status}: {data}")
            break
        batch = data.get("objects") or []
        if not batch:
            break
        items.extend(batch)
        offset += len(batch)
        if len(batch) < 50:
            break
    return items


def docs_from_weaviate(objects):
    docs = []
    for obj in objects:
        props = obj.get("properties") or {}
        vector = obj.get("vector") or []
        rid = props.get("runbook_id") or obj.get("id")
        chunk = props.get("chunk_index")
        doc = {
            "_id": f"{rid}-{chunk}" if chunk is not None else (obj.get("id") or rid),
            "runbook_id": rid,
            "service": props.get("service"),
            "severity": props.get("severity"),
            "source": props.get("source"),
            "text": props.get("text"),
            "chunk_index": chunk,
            "embedding_dims": len(vector) if isinstance(vector, list) else 0,
            "embedding_preview": vector[:8] if isinstance(vector, list) else [],
        }
        if isinstance(vector, list) and len(vector) == 384:
            doc["embedding"] = vector
        docs.append(doc)
    return docs


def docs_from_markdown():
    docs = []
    if not RUNBOOKS_DIR.is_dir():
        return docs
    for path in sorted(RUNBOOKS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        docs.append({
            "_id": path.stem,
            "runbook_id": path.stem,
            "service": None,
            "severity": None,
            "source": path.name,
            "text": text[:8000],
            "chunk_index": 0,
            "embedding_dims": 0,
            "embedding_preview": [],
        })
    return docs


def docs_from_logs():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    docs = []
    paths = []
    if LOGS_DIR.is_dir():
        paths = sorted(list(LOGS_DIR.glob("*.jsonl")) + list(LOGS_DIR.glob("*.log")))
    for path in paths:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                row = {"message": line, "service": path.stem}
            row["@timestamp"] = now
            row.setdefault("timestamp", now)
            row["_id"] = f"{path.stem}-{i}"
            docs.append(row)
    return docs


def ensure_runbooks_index(with_knn):
    mapping = {
        "mappings": {
            "properties": {
                "runbook_id": {"type": "keyword"},
                "service": {"type": "keyword"},
                "severity": {"type": "keyword"},
                "source": {"type": "keyword"},
                "text": {"type": "text"},
                "chunk_index": {"type": "integer"},
                "embedding_dims": {"type": "integer"},
                "embedding_preview": {"type": "float"},
            }
        }
    }
    if with_knn:
        mapping["settings"] = {"index": {"knn": True}}
        mapping["mappings"]["properties"]["embedding"] = {
            "type": "knn_vector",
            "dimension": 384,
            "method": {"name": "hnsw", "space_type": "cosinesimil", "engine": "lucene"},
        }
    delete_index(RUNBOOKS_INDEX)
    if put_index(RUNBOOKS_INDEX, mapping):
        return True
    if with_knn:
        print("retrying runbooks index without k-NN mapping")
        mapping["settings"] = {}
        mapping["mappings"]["properties"].pop("embedding", None)
        delete_index(RUNBOOKS_INDEX)
        return put_index(RUNBOOKS_INDEX, mapping)
    return False


def ensure_logs_index():
    delete_index(LOGS_INDEX)
    return put_index(LOGS_INDEX, {
        "mappings": {
            "properties": {
                "@timestamp": {"type": "date"},
                "timestamp": {"type": "date"},
                "level": {"type": "keyword"},
                "service": {"type": "keyword"},
                "message": {"type": "text"},
            }
        }
    })


def osd_saved_object(kind, sid, attributes):
    status, body = req(
        f"{OSD_URL}/api/saved_objects/{kind}/{sid}?overwrite=true",
        method="POST",
        body={"attributes": attributes},
        headers={"osd-xsrf": "true", "osd-version": "2.17.1"},
    )
    print(f"osd {kind}/{sid} -> {status}")
    return status in (200, 201)


def main():
    wait(f"{OS_URL}/_cluster/health", ok=lambda s, b: s == 200 and b.get("status") in ("green", "yellow"), label="opensearch")
    objects = fetch_weaviate()
    docs = docs_from_weaviate(objects)
    use_knn = any(d.get("embedding") for d in docs)
    if not docs:
        print("weaviate empty — falling back to markdown runbooks")
        docs = docs_from_markdown()
        use_knn = False
    ensure_runbooks_index(with_knn=use_knn)
    n = bulk(RUNBOOKS_INDEX, docs)
    print(f"indexed {n} runbook docs (knn={use_knn})")

    ensure_logs_index()
    logs = docs_from_logs()
    n_logs = bulk(LOGS_INDEX, logs)
    print(f"indexed {n_logs} log docs")

    wait(f"{OSD_URL}/api/status", ok=lambda s, b: s == 200, label="dashboards")
    osd_saved_object("index-pattern", RUNBOOKS_INDEX, {
        "title": RUNBOOKS_INDEX,
    })
    osd_saved_object("index-pattern", LOGS_INDEX, {
        "title": f"{LOGS_INDEX}*",
        "timeFieldName": "@timestamp",
    })
    status, body = req(
        f"{OSD_URL}/api/opensearch-dashboards/settings",
        method="POST",
        body={"changes": {"defaultIndex": RUNBOOKS_INDEX}},
        headers={"osd-xsrf": "true"},
    )
    print(f"osd defaultIndex -> {status} {body}")
    print("seed complete")
    print(f"  runbooks Discover  {OSD_URL}/app/data-explorer/discover")
    print(f"  logs Discover      {OSD_URL}/app/data-explorer/discover")


if __name__ == "__main__":
    main()
