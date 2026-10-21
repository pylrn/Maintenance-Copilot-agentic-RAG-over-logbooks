"""Lossless CSV adapter and deterministic corpus identity."""

import csv
import hashlib
import io
import json
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from maintenance.contracts import CorpusManifest, ParsedCorpus, RecordSnapshot
from maintenance.ingest.normalize import VERSION, normalize

AVIATION_SHA256 = "a70daa27ba9c44a68617d69be1352be7fde003145ca142cbe0b7b51e197c6c3a"
HEADERS = {
    "aviation": ["IDENT", "PROBLEM", "ACTION"],
    "facility": [
        "WORK_ID",
        "SITE_ID",
        "DATE_REQUESTED",
        "PROB_TYPE",
        "DATE_COMPLETED",
        "DESCRIPTION",
    ],
}
URLS = {
    "aviation": "https://people.rit.edu/fa3019/technical/data/maintnet_aviation_dataset_deidentified.csv",
    "facility": "https://people.rit.edu/fa3019/technical/data/Facility_Maintenance200.csv",
}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_source(raw: bytes, domain: str, expected_sha256: str | None = None) -> ParsedCorpus:
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("source checksum mismatch")
    corpus_id = uuid5(NAMESPACE_URL, f"maintenance:{domain}:{digest}")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    if reader.fieldnames != HEADERS[domain]:
        raise ValueError("source header mismatch")
    records, seen = [], set()
    for row_number, row in enumerate(reader, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"malformed CSV row {row_number}")
        source_id = row["IDENT" if domain == "aviation" else "WORK_ID"]
        if (
            not source_id.strip()
            or source_id != source_id.strip()
            or ":" in source_id
            or source_id in seen
        ):
            raise ValueError(f"invalid or duplicate source ID at row {row_number}")
        seen.add(source_id)
        problem = row["PROBLEM" if domain == "aviation" else "DESCRIPTION"]
        action = row.get("ACTION")
        annotations = {"applicability": "unknown"}
        if domain == "facility":
            annotations["site_uncertain"] = row["SITE_ID"].upper() in {"NAN", "", "NULL"}
            for name in ["DATE_REQUESTED", "DATE_COMPLETED"]:
                try:
                    annotations[name.lower()] = (
                        datetime.strptime(
                            row[name], "%m/%d/%y %H:%M" if " " in row[name] else "%m/%d/%y"
                        )
                        .date()
                        .isoformat()
                        if row[name]
                        else None
                    )
                except ValueError as exc:
                    raise ValueError(f"invalid {name} at row {row_number}") from exc
        annotations.update(truncation_annotations(problem, action, domain))
        fields = (
            {"PROBLEM": problem, "ACTION": action}
            if domain == "aviation"
            else {"DESCRIPTION": problem}
        )
        duplicate_key = sha256(
            json.dumps([problem, action], ensure_ascii=False, separators=(",", ":"))
        )
        records.append(
            RecordSnapshot(
                corpus_id=corpus_id,
                record_id=f"{domain}:{source_id}",
                source_id=source_id,
                domain=domain,
                csv_row=row_number,
                original_fields=row,
                problem_raw=problem,
                action_raw=action,
                problem_normalized=normalize(problem, domain),
                action_normalized=normalize(action, domain) if action is not None else None,
                normalization_version=VERSION,
                annotations=annotations,
                duplicate_key=duplicate_key,
                source_file_sha256=digest,
                field_sha256={k: sha256(v) for k, v in fields.items() if v is not None},
            )
        )
    if not records:
        raise ValueError("empty corpus")
    manifest = CorpusManifest(
        corpus_id=corpus_id,
        domain=domain,
        sha256=digest,
        source_url=URLS[domain],
        terms_note="MaintNet research release. Preserve attribution; confirm redistribution rights separately. Not approved maintenance documentation.",
        record_count=len(records),
        distinct_pairs=len({r.duplicate_key for r in records}),
        fields=HEADERS[domain],
    )
    return ParsedCorpus(manifest=manifest, records=records)


def truncation_annotations(problem, action, domain):
    return {
        "possible_truncation_fields": [
            name
            for name, text in [
                ("PROBLEM" if domain == "aviation" else "DESCRIPTION", problem),
                ("ACTION", action),
            ]
            if text and len(text) >= 50 and not text.rstrip().endswith((".", "!", "?"))
        ],
        "truncation_flag_policy": "heuristic/v1; unpunctuated field >=50 characters, never reconstructed",
    }
