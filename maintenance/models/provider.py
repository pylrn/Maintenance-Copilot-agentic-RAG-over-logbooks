"""LLM Provider adapter supporting DeepSeek and Gemini (OpenAI-compatible) and fallback modes."""

import json
import logging
from typing import Any, Callable, Literal
from urllib.parse import urlparse

from openai import AsyncOpenAI
from pydantic import SecretStr

logger = logging.getLogger("maintenance.provider")

PROVIDER_ENDPOINTS = {
    "deepseek": "https://api.deepseek.com",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}

PROVIDER_MODELS = {
    "deepseek": ["deepseek-flash"],
    "gemini": ["gemini-3.5-flash", "gemini-3.7-flash", "gemini-3.8-flash", "gemini-2.5-flash"],
}


class LLMProvider:
    def __init__(
        self,
        api_key: SecretStr | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        provider_type: Literal["auto", "deepseek", "gemini"] = "auto",
    ):
        raw_key = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
        self.api_key = raw_key if raw_key and not raw_key.startswith("REPLACE") else None

        # Resolve provider type
        resolved_type: Literal["deepseek", "gemini"]
        if provider_type in ("deepseek", "gemini"):
            resolved_type = provider_type
        elif model_name and "gemini" in model_name.lower():
            resolved_type = "gemini"
        elif base_url and "googleapis.com" in base_url:
            resolved_type = "gemini"
        else:
            resolved_type = "deepseek"

        self.provider_type = resolved_type
        self.base_url = (
            base_url
            if base_url
            else PROVIDER_ENDPOINTS[self.provider_type]
        )
        self.model_name = (
            model_name
            if model_name
            else PROVIDER_MODELS[self.provider_type][0]
        )

        # Validate exact HTTPS endpoint and model allowlist per provider
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https":
            raise ValueError(f"provider endpoint must use HTTPS: {self.base_url}")
        expected_endpoint = PROVIDER_ENDPOINTS[self.provider_type]
        if self.base_url != expected_endpoint:
            raise ValueError(
                f"disallowed provider base_url: {self.base_url}; expected {expected_endpoint}"
            )
        allowed_models = PROVIDER_MODELS[self.provider_type]
        if self.model_name not in allowed_models:
            raise ValueError(
                f"model '{self.model_name}' not in {self.provider_type} allowlist: {allowed_models}"
            )

        self.client: AsyncOpenAI | None = None
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, max_retries=0)

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def __repr__(self) -> str:
        key_status = "configured" if self.is_configured else "unconfigured"
        return f"<LLMProvider type={self.provider_type} model={self.model_name} key={key_status}>"

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Calls the configured OpenAI-compatible chat completions endpoint."""
        if not self.is_configured:
            raise RuntimeError(
                f"provider_not_configured: {self.provider_type.upper()}_API_KEY is missing or placeholder."
            )

        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "timeout": timeout,
        }
        if self.provider_type == "deepseek":
            # DeepSeek non-thinking mode per documentation
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = await self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message

            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tc_dict = {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    if hasattr(tc, "extra_content") and tc.extra_content:
                        tc_dict["extra_content"] = tc.extra_content
                    tool_calls.append(tc_dict)

            return {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": tool_calls,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                },
            }
        except Exception as exc:
            logger.error("LLM provider completion error (%s): %s", self.provider_type, type(exc).__name__)
            raise

    async def roundtrip_tool_loop(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_dispatch: dict[str, Callable[[dict[str, Any]], Any]],
        max_turns: int = 3,
        max_tool_calls: int = 8,
        deadline_seconds: float = 30.0,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Executes a bounded native tool-calling roundtrip retaining exact tool call IDs."""
        import asyncio
        import time

        start_time = time.perf_counter()
        current_messages = list(messages)
        final_response: dict[str, Any] = {}
        total_calls = 0

        async def _run_loop():
            nonlocal final_response, total_calls, current_messages
            for _ in range(max_turns):
                elapsed = time.perf_counter() - start_time
                if elapsed >= deadline_seconds:
                    break
                rem = max(0.5, deadline_seconds - elapsed)

                final_response = await self.chat_completion(
                    current_messages, tools=tools, timeout=rem
                )
                tool_calls = final_response.get("tool_calls", [])
                if not tool_calls:
                    break

                assistant_tool_calls = []
                for tc in tool_calls:
                    call_entry = {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        },
                    }
                    if "extra_content" in tc and tc["extra_content"]:
                        call_entry["extra_content"] = tc["extra_content"]
                    assistant_tool_calls.append(call_entry)

                current_messages.append(
                    {
                        "role": "assistant",
                        "content": final_response.get("content") or "",
                        "tool_calls": assistant_tool_calls,
                    }
                )

                budget_exhausted = False
                for tc in tool_calls:
                    call_id = tc["id"]
                    fn_name = tc["function"]["name"]
                    raw_args = tc["function"]["arguments"]

                    if total_calls >= max_tool_calls or (time.perf_counter() - start_time) >= deadline_seconds:
                        budget_exhausted = True
                        res = {"error": "tool_budget_exhausted"}
                    else:
                        total_calls += 1
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        handler = tool_dispatch.get(fn_name)
                        if handler:
                            rem_tool = max(0.1, deadline_seconds - (time.perf_counter() - start_time))
                            if asyncio.iscoroutinefunction(handler) or hasattr(handler, "__await__"):
                                res = await asyncio.wait_for(handler(args), timeout=rem_tool)
                            elif callable(handler):
                                res = handler(args)
                            else:
                                res = handler
                        else:
                            res = {"error": f"tool_not_found: {fn_name}"}

                    current_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": fn_name,
                            "content": json.dumps(res) if not isinstance(res, str) else res,
                        }
                    )

                if budget_exhausted or total_calls >= max_tool_calls:
                    break

        try:
            await asyncio.wait_for(_run_loop(), timeout=deadline_seconds)
        except (asyncio.TimeoutError, TimeoutError):
            pass

        return final_response, current_messages
