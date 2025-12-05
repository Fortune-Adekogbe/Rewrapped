"""
Manual sanity checks for the Rewrapped API.

Run after starting the server (uvicorn or Docker) to quickly verify endpoints.
Usage:
    REWRAPPED_BASE_URL=http://localhost:8000 python manual_test.py
"""

import json
import os

import httpx


BASE_URL = os.getenv("REWRAPPED_BASE_URL", "http://localhost:8000")


def preview(data: object, limit: int = 600) -> str:
    text = json.dumps(data, indent=2, default=str)
    if len(text) > limit:
        return text[:limit] + "... (truncated)"
    return text


def main() -> None:
    with httpx.Client(timeout=30) as client:
        print(f"Base URL: {BASE_URL}")

        health = client.get(f"{BASE_URL}/health")
        print(f"\nGET /health -> {health.status_code}")
        print(health.text)

        endpoints = [
            ("/wrapped/short", {"top_limit": 5, "recent_limit": 20}),
            # ("/wrapped/medium", {"top_limit": 5}),
            # ("/wrapped/long", {"top_limit": 5}),
        ]
        for path, params in endpoints:
            resp = client.get(f"{BASE_URL}{path}", params=params)
            print(f"\nGET {path} -> {resp.status_code}")
            try:
                print(preview(resp.json()))
            except Exception:
                print(resp.text)


if __name__ == "__main__":
    main()
