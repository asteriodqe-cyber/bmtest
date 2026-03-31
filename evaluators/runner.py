from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1/chat/completions"
MOONSHOT_MODEL = "kimi-k2.5"
MOONSHOT_TEMPERATURE = 1
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 90


@dataclass
class AgentExecutionResult:
    """Surrogate Agent 执行结果的标准结构"""
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    execution_trace: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def load_skill(skill_path: str) -> str:
    """读取 SKILL.md 内容作为系统提示"""
    path = Path(skill_path)
    if not path.exists():
        raise FileNotFoundError(f"Skill file not found: {skill_path}")
    return path.read_text(encoding="utf-8")


def compute_sha256(skill_path: str) -> str:
    """计算 Skill 文件的 SHA256 hash，用于版本溯源"""
    content = Path(skill_path).read_bytes()
    return f"sha256:{hashlib.sha256(content).hexdigest()[:16]}"


def build_metadata(
    skill_path: str,
    provider: str,
    model: str,
    temperature: float,
    n_runs: int
) -> dict:
    """构建实验元数据"""
    return {
        "surrogate_agent": model,
        "api_provider": provider,
        "temperature": temperature,
        "thinking_mode": "instant",
        "timestamp": time.strftime("%Y-%m-%d"),
        "n_runs": n_runs,
        "skill_hash": compute_sha256(skill_path)
    }


async def _call_kimi_stream(
    session,
    system_prompt: str,
    user_prompt: str,
    attempt: int = 0
) -> str:
    """
    单次 Kimi API 流式调用

    使用流式传输解决超时问题：
    - 非流式：等待全部生成完才返回，长 PRD 容易超时
    - 流式：边生成边接收，timeout 只需覆盖第一个 token
    """
    import aiohttp

    # .strip() 防止换行符或空格导致 header injection 错误
    api_key = os.environ.get("MOONSHOT_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "MOONSHOT_API_KEY not set. "
            "Please add it to your .env file."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MOONSHOT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": MOONSHOT_TEMPERATURE,
        "max_tokens": 4096,
        "stream": True
    }

    timeout = aiohttp.ClientTimeout(
        connect=CONNECT_TIMEOUT,
        sock_read=READ_TIMEOUT
    )

    content_parts = []

    async with session.post(
        MOONSHOT_BASE_URL,
        headers=headers,
        json=payload,
        timeout=timeout
    ) as resp:
        if resp.status == 429:
            raise Exception(f"429: Engine overloaded")
        if resp.status != 200:
            text = await resp.text()
            raise Exception(f"HTTP {resp.status}: {text[:200]}")

        async for line in resp.content:
            line = line.decode("utf-8").strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                delta = chunk["choices"][0]["delta"]
                if delta.get("content"):
                    content_parts.append(delta["content"])
            except (json.JSONDecodeError, KeyError):
                continue

    return "".join(content_parts)


async def _call_kimi_with_retry(
    session,
    system_prompt: str,
    user_prompt: str,
    max_attempts: int = 3
) -> str:
    """
    带重试的 Kimi 调用

    重试策略：
    - 429 过载：等待 30s / 60s / 90s + 随机抖动
    - 其他错误：等待 2s / 4s
    - EnvironmentError：不重试
    """
    import random

    last_error = None
    for attempt in range(max_attempts):
        try:
            return await _call_kimi_stream(session, system_prompt, user_prompt, attempt)
        except EnvironmentError:
            raise
        except Exception as e:
            last_error = e
            error_str = str(e)

            if attempt < max_attempts - 1:
                if "429" in error_str or "overloaded" in error_str.lower():
                    wait = 30 * (attempt + 1) + random.uniform(0, 10)
                else:
                    wait = 2 ** (attempt + 1)
                print(f"    [RETRY {attempt + 2}/{max_attempts}] {error_str[:60]}, waiting {wait:.1f}s...")
                await asyncio.sleep(wait)

    raise last_error


async def run_surrogate_agent(
    session,
    skill_path: str,
    user_input: str,
    use_skill: bool = True
) -> AgentExecutionResult:
    """
    统一的 Agent 执行接口（async）

    Args:
        session:     aiohttp.ClientSession 实例
        skill_path:  SKILL.md 文件路径
        user_input:  用户任务描述
        use_skill:   True = with_skill 条件，False = baseline 条件
    """
    if use_skill:
        system_prompt = load_skill(skill_path)
    else:
        system_prompt = "你是一个产品经理助手，帮助用户撰写产品文档。"

    content = await _call_kimi_with_retry(session, system_prompt, user_input)

    return AgentExecutionResult(
        content=content,
        metadata={"model": MOONSHOT_MODEL}
    )
