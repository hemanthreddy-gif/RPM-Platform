"""Post clearly synthetic device readings to the local Phase 9 device endpoint."""

import argparse
import json
from datetime import UTC, datetime, timedelta
from time import sleep
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic RPM device simulator; not for real devices")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--type", choices=("glucose", "blood_pressure"), default="glucose")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--duplicates", type=int, default=0)
    parser.add_argument("--out-of-order", action="store_true")
    parser.add_argument("--offline-seconds", type=float, default=0)
    args = parser.parse_args()
    if args.count < 1 or args.duplicates < 0 or args.offline_seconds < 0:
        parser.error("count/offline-seconds must be positive and duplicates cannot be negative")
    readings = []
    for index in range(args.count):
        measured_at = datetime.now(UTC) - timedelta(minutes=index if args.out_of_order else 0)
        payload = {"type": args.type, "unit": "mg/dL", "value": 100 + index, "measured_at": measured_at.isoformat()}
        if args.type == "blood_pressure":
            payload = {"type": args.type, "unit": "mmHg", "components": {"systolic": 120 + index, "diastolic": 80}, "measured_at": measured_at.isoformat()}
        readings.append((payload, str(uuid4())))
    if args.offline_seconds:
        sleep(args.offline_seconds)
    for payload, key in readings:
        for _ in range(args.duplicates + 1):
            request = Request(f"{args.base_url}/api/v1/devices/{args.device_id}/readings", data=json.dumps(payload).encode(), method="POST", headers={"Content-Type": "application/json", "X-Device-Token": args.token, "Idempotency-Key": key})
            try:
                with urlopen(request, timeout=15) as response:
                    print(response.status)
            except HTTPError as error:
                raise SystemExit(f"device ingestion failed: {error.code}") from error


if __name__ == "__main__":
    main()
