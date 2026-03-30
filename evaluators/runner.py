from __future__ import annotations

import os
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_not_exception_type
)


@dataclass
class AgentExecutionResult:
    """Surrogate Agent 执行结果的标准结构"""
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    execution_trace: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    raw_response: Any = None


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
        "thinking_mode": "instant" if provider == "moonshot" else "default",
        "timestamp": time.strftime("%Y-%m-%d"),
        "n_runs": n_runs,
        "skill_hash": compute_sha256(skill_path)
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_not_exception_type((ValueError, EnvironmentError))
)
def _call_moonshot(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float
) -> AgentExecutionResult:
    """
    调用 Kimi API（中国平台）

    kimi-k2.5 instant mode 强制要求 temperature=0.6
    retry 不重试 ValueError 和 EnvironmentError（配置错误，重试无意义）
    """
    from openai import OpenAI

    api_key = os.environ.get("MOONSHOT_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "MOONSHOT_API_KEY not set. "
            "Get your key from https://platform.moonshot.cn"
        )

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.moonshot.cn/v1"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.6,
        max_tokens=4096,
        timeout=60,
        extra_body={"thinking": {"type": "disabled"}}
    )

    content = response.choices[0].message.content or ""
    tool_calls = []

    if response.choices[0].message.tool_calls:
        tool_calls = [
            {
                "tool_name": tc.function.name,
                "arguments": tc.function.arguments,
                "timestamp": time.time()
            }
            for tc in response.choices[0].message.tool_calls
        ]

    return AgentExecutionResult(
        content=content,
        tool_calls=tool_calls,
        metadata={
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "model": response.model
        },
        raw_response=response
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_not_exception_type((ValueError, EnvironmentError))
)
def _call_anthropic(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float
) -> AgentExecutionResult:
    """
    调用 Claude API

    retry 不重试 ValueError 和 EnvironmentError（配置错误，重试无意义）
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. "
            "Get your key from https://console.anthropic.com"
        )

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        timeout=60
    )

    content = response.content[0].text if response.content else ""

    return AgentExecutionResult(
        content=content,
        tool_calls=[],
        metadata={
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "model": response.model
        },
        raw_response=response
    )


def run_surrogate_agent(
    skill_path: str,
    user_input: str,
    provider: str = "moonshot",
    model: str = "kimi-k2.5",
    temperature: float = 0.6,
    use_skill: bool = True
) -> AgentExecutionResult:
    """
    统一的 Agent 执行接口

    Args:
        skill_path:  SKILL.md 文件路径
        user_input:  用户任务描述
        provider:    API 提供方，moonshot 或 anthropic
        model:       模型名称，默认 kimi-k2.5
        temperature: 采样温度（moonshot 固定使用 0.6）
        use_skill:   True = with_skill 条件，False = baseline 条件
    """
    if use_skill:
        system_prompt = load_skill(skill_path)
    else:
        system_prompt = "你是一个产品经理助手，帮助用户撰写产品文档。"

    if provider == "moonshot":
        temperature = 0.6

    if provider == "moonshot":
        return _call_moonshot(system_prompt, user_input, model, temperature)
    elif provider == "anthropic":
        return _call_anthropic(system_prompt, user_input, model, temperature)
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. Use 'moonshot' or 'anthropic'."
        )
