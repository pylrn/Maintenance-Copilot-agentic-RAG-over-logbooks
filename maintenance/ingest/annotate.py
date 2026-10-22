"""Conservative search annotations. Internal tags are not reviewed visual mappings."""

import re

from maintenance.contracts import Mention

COMPONENTS = {
    "intake": r"\b(?:intake|induction)\b",
    "rocker_cover": r"\b(?:rocker\s+(?:box\s+)?cover|valve\s+cover)s?\b",
    "baffle": r"\bbaffles?\b",
    "battery": r"\bbattery\b",
    "brake": r"\bbrakes?\b",
    "magneto": r"\b(?:magnetos?|mags?)\b",
    "spark_plug": r"\b(?:spark\s+)?plugs?\b",
    "alternator": r"\b(?:alternator|alt)\b",
    "dipstick": r"\bdipstick\b",
    "cowling": r"\b(?:cowl|cowling)\b",
    "fuel_servo": r"\bfuel\s+servo\b",
}
SYMPTOMS = {
    "leak": r"\bleak(?:s|ing)?\b",
    "crack": r"\bcrack(?:s|ed)?\b",
    "loose": r"\bloose\b",
    "rough": r"\brough\b",
    "torn": r"\btorn\b",
    "missing": r"\bmissing\b",
    "inoperative": r"\b(?:inop|inoperative)\b",
    "idle": r"\bidle\b",
    "flat": r"\bflat\b",
}


def mentions(text: str) -> list[Mention]:
    result = []
    for kind, patterns in [("component", COMPONENTS), ("symptom", SYMPTOMS)]:
        for value, pattern in patterns.items():
            for m in re.finditer(pattern, text, re.I):
                result.append(
                    Mention(value=value, text=m.group(), start=m.start(), end=m.end(), kind=kind)
                )
    for m in re.finditer(
        r"(?:(cyl(?:inder)?|eng(?:ine)?)\s*)?#\s*(\d+)|\b(cyl(?:inder)?|eng(?:ine)?)\s+(\d+)\b",
        text,
        re.I,
    ):
        prefix = (m.group(1) or m.group(3) or "").lower()
        number = m.group(2) or m.group(4)
        kind = (
            "cylinder_number"
            if prefix.startswith("cyl")
            else "engine_number"
            if prefix.startswith("eng")
            else "number"
        )
        result.append(
            Mention(value=number, text=m.group(), start=m.start(), end=m.end(), kind=kind)
        )
    for m in re.finditer(r"\b(?:r/h|l/h|right|left)\b", text, re.I):
        result.append(
            Mention(
                value="right" if m.group().lower() in {"r/h", "right"} else "left",
                text=m.group(),
                start=m.start(),
                end=m.end(),
                kind="laterality",
            )
        )
    for m in re.finditer(r"\b(?:no|not|without|never)\b", text, re.I):
        result.append(
            Mention(
                value=m.group().lower(),
                text=m.group(),
                start=m.start(),
                end=m.end(),
                kind="negation",
            )
        )
    return sorted(result, key=lambda m: (m.start, m.end, m.kind))
