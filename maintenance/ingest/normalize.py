import json
import re
from pathlib import Path

_RULES = json.loads((Path(__file__).resolve().parents[2] / "config/abbreviations.json").read_text())
VERSION = _RULES["version"]


def normalize(text: str, domain: str) -> str:
    mapping = _RULES[domain]
    if mapping:
        pattern = (
            r"(?<![\w/])(?:"
            + "|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True))
            + r")(?![\w/])"
        )
        text = re.sub(pattern, lambda m: mapping[m.group().lower()], text, flags=re.I)
    return " ".join(text.lower().split())


def tokenize(text: str) -> list[str]:
    return re.findall(r"#[0-9]+|[a-z]+/[a-z]+|[a-z0-9]+(?:-[a-z0-9]+)*", text.lower())
