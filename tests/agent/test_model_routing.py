from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from openai import RateLimitError
from pydantic import SecretStr

from maintenance.models.provider import LLMProvider


def response(model):
    return SimpleNamespace(model=model,choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{}',tool_calls=[]))],
        usage=SimpleNamespace(prompt_tokens=10,completion_tokens=20,completion_tokens_details=SimpleNamespace(reasoning_tokens=12)))


@pytest.mark.asyncio
async def test_requested_model_reasoning_and_output_budget_reach_provider_unchanged():
    p=LLMProvider(SecretStr('test'),'https://generativelanguage.googleapis.com/v1beta/openai/','gemini-3.8-flash','gemini')
    p._traced_completion=AsyncMock(return_value=response('gemini-3.8-flash'))
    result=await p.chat_completion([],reasoning_effort='low',max_tokens=3072)
    assert p.model_name=='gemini-3.8-flash'
    assert p._traced_completion.call_args.kwargs['model']=='gemini-3.8-flash'
    assert p._traced_completion.call_args.kwargs['reasoning_effort']=='low'
    assert p._traced_completion.call_args.kwargs['max_tokens']==3072
    assert result['requested_model']==result['effective_model']=='gemini-3.8-flash'
    assert result['usage']['reasoning_tokens']==12 and not result['fallback']
    await p.client.close()


@pytest.mark.asyncio
async def test_429_is_not_retried_or_substituted_by_default():
    p=LLMProvider(SecretStr('test'),model_name='gemini-3.8-flash',provider_type='gemini')
    exc=RateLimitError('quota',response=httpx.Response(429,request=httpx.Request('POST','https://example.test')),body=None)
    p._traced_completion=AsyncMock(side_effect=exc)
    with pytest.raises(RateLimitError):await p.chat_completion([])
    p._traced_completion.assert_awaited_once()
    await p.client.close()


@pytest.mark.asyncio
async def test_opt_in_fallback_is_disclosed():
    p=LLMProvider(SecretStr('test'),model_name='gemini-3.8-flash',provider_type='gemini')
    exc=RateLimitError('quota',response=httpx.Response(429,request=httpx.Request('POST','https://example.test')),body=None)
    p._traced_completion=AsyncMock(side_effect=[exc,response('gemini-3.5-flash-lite')])
    result=await p.chat_completion([],allow_fallback=True)
    assert p._traced_completion.await_count==2
    assert result['requested_model']=='gemini-3.8-flash'
    assert result['effective_model']=='gemini-3.5-flash-lite' and result['fallback']
    await p.client.close()


def test_benchmark_enforces_rolling_limits_and_disables_exhausted_model():
    from maintenance.benchmark_limits import BenchmarkLimits
    limits=BenchmarkLimits()
    limits.record('gemini-3.8-flash',0);limits.record('gemini-3.8-flash',1)
    assert limits.delay('gemini-3.8-flash',2)>58
    with pytest.raises(ValueError):limits.record('gemini-3.8-flash',2)
    limits.record('gemini-3.5-flash-lite',2);limits.record('gemini-3.5-flash-lite',3)
    assert limits.delay('gemini-3.5-flash-lite',4)>56
    assert limits.delay('gemini-3.8-flash',61.2)==0
    limits.disabled.add('gemini-3.8-flash')
    with pytest.raises(ValueError):limits.delay('gemini-3.8-flash',100)
