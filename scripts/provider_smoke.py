"""Smoke test for LLM provider (DeepSeek and Gemini), tool execution and ID retention."""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from maintenance.agent import AGENT_TOOLS  # noqa: E402
from maintenance.config import Settings  # noqa: E402
from maintenance.models.provider import LLMProvider  # noqa: E402


async def run_smoke(model_arg: str):
    settings = Settings()
    ptype = "gemini" if "gemini" in model_arg.lower() else "deepseek"
    model = model_arg.split(":")[-1] if ":" in model_arg else model_arg

    if ptype == "gemini":
        key = settings.gemini_api_key
        base_url = settings.gemini_base_url
    else:
        key = settings.deepseek_api_key
        base_url = settings.deepseek_base_url

    print(f"Provider: {ptype}")
    print(f"Testing model: {model}")
    print(f"Base URL: {base_url}")
    print(f"Configured: {bool(key and key.get_secret_value() and not key.get_secret_value().startswith('REPLACE'))}")

    provider = LLMProvider(
        api_key=key,
        base_url=base_url,
        model_name=model,
        provider_type=ptype,
    )

    if not provider.is_configured:
        print(f"[SKIPPED] {ptype.upper()}_API_KEY is not configured. Live provider call skipped.")
        return 0

    messages = [
        {"role": "system", "content": "You are Maintenance Atlas. Call the search tool to find records."},
        {"role": "user", "content": "Cylinder #2 intake is leaking. Search records."},
    ]

    try:
        resp = await provider.chat_completion(messages=messages, tools=AGENT_TOOLS)
        print("[SUCCESS] Provider call completed successfully.")
        print("Response role:", resp.get("role"))
        tool_calls = resp.get("tool_calls", [])
        print("Tool calls returned:", len(tool_calls))
        for tc in tool_calls:
            print(f" - Tool: {tc['function']['name']}, Args: {tc['function']['arguments']}, ID: {tc['id']}")

        # Test tool roundtrip if tool calls were emitted
        if tool_calls:
            print("Testing tool response roundtrip...")
            roundtrip_messages = list(messages)
            assistant_tcs = []
            for tc in tool_calls:
                entry = {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    },
                }
                if "extra_content" in tc and tc["extra_content"]:
                    entry["extra_content"] = tc["extra_content"]
                assistant_tcs.append(entry)

            roundtrip_messages.append(
                {
                    "role": "assistant",
                    "content": resp.get("content") or "",
                    "tool_calls": assistant_tcs,
                }
            )
            for tc in tool_calls:
                roundtrip_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": tc["function"]["name"],
                        "content": '{"status": "ok", "hit_count": 1, "record_ids": ["aviation:100009"]}',
                    }
                )
            followup = await provider.chat_completion(messages=roundtrip_messages)
            print("[SUCCESS] Followup after tool execution succeeded.")
            print("Followup content snippet:", (followup.get("content") or "")[:80])

        return 0
    except Exception as exc:
        status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        status_info = f" (status={status})" if status else ""
        print(f"[ERROR] Provider call failed: {type(exc).__name__}{status_info}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM Provider Smoke Test")
    parser.add_argument("--model", default="deepseek-flash", help="Model name or provider:model")
    args = parser.parse_args()
    code = asyncio.run(run_smoke(args.model))
    sys.exit(code)
