#!/usr/bin/env python3
"""Simple load test script for /api/v1/analyze using stdlib only."""

from __future__ import annotations

import argparse
import concurrent.futures
import time
import uuid
from pathlib import Path
from typing import Tuple
from urllib import request


def build_multipart(image_path: Path, modules: str = "all") -> Tuple[bytes, str]:
    boundary = f"----ImageGuardBoundary{uuid.uuid4().hex}"
    with image_path.open("rb") as f:
        image_bytes = f.read()

    lines = []
    lines.append(f"--{boundary}")
    lines.append('Content-Disposition: form-data; name="modules"')
    lines.append("")
    lines.append(modules)
    lines.append(f"--{boundary}")
    lines.append(f'Content-Disposition: form-data; name="image"; filename="{image_path.name}"')
    lines.append("Content-Type: application/octet-stream")
    lines.append("")
    body = "\r\n".join(lines).encode("utf-8") + b"\r\n" + image_bytes + b"\r\n"
    body += f"--{boundary}--\r\n".encode("utf-8")
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def send_request(url: str, image_path: Path, modules: str) -> float:
    body, content_type = build_multipart(image_path, modules)
    req = request.Request(url, data=body, headers={"Content-Type": content_type}, method="POST")
    start = time.perf_counter()
    with request.urlopen(req, timeout=30) as resp:
        resp.read()
    return (time.perf_counter() - start) * 1000


def main() -> int:
    parser = argparse.ArgumentParser(description="Load test ImageGuard API")
    parser.add_argument("--url", default="http://localhost:8080/api/v1/analyze")
    parser.add_argument("--image", required=True, help="Path to image file")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--modules", default="all")
    args = parser.parse_args()

    image_path = Path(args.image)
    latencies = []
    errors = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = [ex.submit(send_request, args.url, image_path, args.modules) for _ in range(args.requests)]
        for f in concurrent.futures.as_completed(futures):
            try:
                latencies.append(f.result())
            except Exception:
                errors += 1

    if latencies:
        latencies.sort()
        p95 = latencies[int(0.95 * len(latencies)) - 1]
        avg = sum(latencies) / len(latencies)
    else:
        p95 = 0
        avg = 0

    print(f"requests={args.requests} concurrency={args.concurrency} errors={errors}")
    print(f"avg_ms={avg:.2f} p95_ms={p95:.2f} samples={len(latencies)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
