from __future__ import annotations

import os
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path


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


def _call_moonshot(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float
) -> AgentExecutionResult:
    """
    调用 Kimi API（流式传输版本）

    使用 stream=True 解决超时问题：
    - 非流式：等待全部内容生成完才返回，生成长 PRD 时容易超时
    - 流式：边生成边接收，timeout 只需覆盖第一个 token 的等待时间
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

    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.6,
        max_tokens=4096,
        timeout=60,  # 流式模式下只需等第一个 token，60s 足够
        stream=True,
        extra_body={"thinking": {"type": "disabled"}}
    )

    # 逐块收集流式输出
    content_parts = []
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            content_parts.append(delta.content)

    content = "".join(content_parts)

    return AgentExecutionResult(
        content=content,
        tool_calls=[],
        metadata={
            "model": model
        },
        raw_response=None
    )


def _call_anthropic(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float
) -> AgentExecutionResult:
    """调用 Claude API 单次调用"""
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
        timeout=120
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
        raw_response=None
    )


def _call_with_retry(
    call_fn,
    *args,
    max_attempts: int = 3
) -> AgentExecutionResult:
    """
    手动重试机制

    重试策略：
    - 429 过载：等待 30s / 60s / 90s
    - 其他错误：等待 1s / 2s
    - ValueError / EnvironmentError：不重试
    """
    last_error = None
    for attempt in range(max_attempts):
        try:
            return call_fn(*args)
        except (ValueError, EnvironmentError):
            raise
        except Exception as e:
            last_error = e
            error_str = str(e)

            if attempt < max_attempts - 1:
                if "429" in error_str or "overloaded" in error_str.lower():
                    wait = 30 * (attempt + 1)
                    print(f"    [429] Engine overloaded, waiting {wait}s before retry {attempt + 2}/{max_attempts}...")
                else:
                    wait = 2 ** attempt
                    print(f"    [RETRY] {error_str[:60]}, waiting {wait}s before retry {attempt + 2}/{max_attempts}...")
                time.sleep(wait)
            else:
                print(f"    [FAILED] All {max_attempts} attempts failed: {error_str[:80]}")

    raise last_error


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
        return _call_with_retry(_call_moonshot, system_prompt, user_input, model, temperature)
    elif provider == "anthropic":
        return _call_with_retry(_call_anthropic, system_prompt, user_input, model, temperature)
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. Use 'moonshot' or 'anthropic'."
        )
