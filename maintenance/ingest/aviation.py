from maintenance.ingest.manifest import parse_source


def parse_aviation(raw: bytes, expected_sha256: str | None = None):
    return parse_source(raw, "aviation", expected_sha256)
