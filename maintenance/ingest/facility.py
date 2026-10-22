from maintenance.ingest.manifest import parse_source


def parse_facility(raw: bytes, expected_sha256: str | None = None):
    return parse_source(raw, "facility", expected_sha256)
