"""Maintenance Atlas agent harness and tool registries."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get_system_prompt() -> str:
    prompt_path = ROOT / "docs/prompts/maintenance_system_prompt.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return "You are Maintenance Atlas, an evidence-first maintenance copilot."


AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_records",
            "description": "Search historical maintenance records using BM25 and dense retrieval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Fault description or complaint."},
                    "domain": {"type": "string", "enum": ["aviation", "facility"], "default": "aviation"},
                    "top_k": {"type": "integer", "default": 6},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_records",
            "description": "Fetch exact authoritative raw records and register evidence snapshots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "record_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of namespaced record IDs.",
                    }
                },
                "required": ["record_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_records",
            "description": "Compare grounded problem and action text between 2 to 6 records.",
            "parameters": {
                "type": "object",
                "properties": {
                    "record_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["record_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pattern_summary",
            "description": "Calculate recurring corpus pattern counts and distinct problem/action groups.",
            "parameters": {
                "type": "object",
                "properties": {
                    "component": {"type": "string"},
                    "domain": {"type": "string", "default": "aviation"},
                },
                "required": ["component"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_component_context",
            "description": "Retrieve reviewed educational component context and visual mapping hotspots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "component_id": {"type": "string"},
                },
                "required": ["component_id"],
            },
        },
    },
]
