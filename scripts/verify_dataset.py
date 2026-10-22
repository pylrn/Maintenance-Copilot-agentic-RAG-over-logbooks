import argparse
import json
from pathlib import Path

from maintenance.ingest.aviation import parse_aviation
from maintenance.ingest.facility import parse_facility

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--domain", required=True, choices=["aviation", "facility"])
    p.add_argument("--expected-sha256")
    a = p.parse_args()
    c = (parse_aviation if a.domain == "aviation" else parse_facility)(
        Path(a.source).read_bytes(), a.expected_sha256
    )
    print(json.dumps(c.manifest.model_dump(mode="json"), indent=2))
