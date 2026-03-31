from __future__ import annotations

import os
import json
import re
import time

from evaluators.assertion_checker import load_assertions


JUDGE_SYSTEM_PROMPT = """你是一个严格的产品文档评估专家。
你的任务是判断给定的文档内容是否满足特定的断言条件。

规则：
1. 只返回 JSON 格式，不要有任何其他文字
2. 如果满足断言，confidence 在 0.7-1.0 之间
3. 如果不满足，confidence 在 0.0-0.3 之间
4. 部分满足时，confidence 在 0.4-0.6 之间
5. 判断要基于文档实际内容，不要推测未写出的内容
6. 如果文档内容标注为部分样本，请基于可见内容进行判断，不要因内容不完整而降低 confidence
"""


# ── 内容采样 ──────────────────────────────────────────────

def _sample_content(content: str, max_chars: int = 3000) -> tuple[str, bool]:
    """
    对超长内容进行首尾采样

    Returns:
        (sampled_content, is_sampled)
    """
    if len(content) <= max_chars:
        return content, False
    head = content[:1200]
    tail = content[-800:]
    return f"{head}\n...[中间省略]...\n{tail}", True


# ── Judge Prompt 构建 ─────────────────────────────────────

def build_judge_prompt(content: str, assertion: dict) -> str:
    """构建 LLM judge 的评估 prompt"""
    sample, is_sampled = _sample_content(content)

    sampling_note = ""
    if is_sampled:
        sampling_note = (
            "\n【注意】文档较长，以下仅显示首尾部分用于评估。"
            "请基于可见内容进行判断，不要因内容不完整而降低 confidence。\n"
        )

    return f"""请判断以下文档是否满足断言条件。

【断言条件】
{assertion['check']}
{sampling_note}
【文档内容】
{sample}

请返回以下 JSON 格式，不要包含任何其他文字：
{{
    "passed": true或false,
    "confidence": 0到1之间的浮点数,
    "reason": "简短的判断理由（20字以内）"
}}

注意：如果文档结构混乱或条件只部分满足，请给出 0.4-0.6 之间的 confidence。"""


# ── LLM 单次调用 ──────────────────────────────────────────

def _call_judge_once(prompt: str, provider: str = "moonshot") -> dict:
    """单次 LLM judge 调用，不含重试逻辑"""
    raw = ""

    if provider == "moonshot":
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
            model="kimi-k2.5",
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=256,
            timeout=60,
            extra_body={"thinking": {"type": "disabled"}}
        )
        raw = response.choices[0].message.content or "{}"

    elif provider == "anthropic":
        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY not set. "
                "Get your key from https://console.anthropic.com"
            )

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            temperature=0.6,
            system=JUDGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            timeout=60
        )
        raw = response.content[0].text if response.content else "{}"

    else:
        raise ValueError(f"Unsupported provider: {provider}")

    raw = raw.strip()
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)

    try:
        result = json.loads(raw)
        return {
            "passed": bool(result.get("passed", False)),
            "confidence": float(result.get("confidence", 0.0)),
            "reason": str(result.get("reason", ""))[:100]
        }
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "passed": False,
            "confidence": 0.0,
            "reason": f"Parse error: {str(e)[:50]}"
        }


def _call_judge(prompt: str, provider: str = "moonshot") -> dict:
    """
    调用 LLM judge，含手动重试

    使用手动重试替代 tenacity @retry，避免 RLock 在
    Python 3.14 spawn 模式下的 pickle 序列化问题。
    """
    last_error = None
    for attempt in range(3):
        try:
            return _call_judge_once(prompt, provider)
        except (ValueError, EnvironmentError):
            raise
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise last_error


# ── 单条 LLM 断言执行 ─────────────────────────────────────

def run_llm_assertion(
    content: str,
    assertion: dict,
    provider: str = "moonshot"
) -> dict:
    """执行单条 llm 类断言，返回部分得分"""
    required_fields = ["id", "check"]
    for required_field in required_fields:
        if required_field not in assertion:
            return {
                "id": assertion.get("id", "unknown"),
                "type": "error",
                "method": "llm",
                "passed": False,
                "confidence": 0.0,
                "score": 0,
                "max_score": assertion.get("points", 2),
                "reason": f"Missing required field: {required_field}"
            }

    assertion_id = assertion["id"]
    points = assertion.get("points", 2)

    prompt = build_judge_prompt(content, assertion)
    judgment = _call_judge(prompt, provider)

    passed = judgment["passed"]
    confidence = judgment["confidence"]
    reason = judgment["reason"]
    score = round(points * confidence, 2)

    return {
        "id": assertion_id,
        "type": assertion.get("type", "completeness"),
        "method": "llm",
        "passed": passed,
        "confidence": confidence,
        "score": score,
        "max_score": points,
        "reason": reason
    }


# ── 批量 LLM 断言执行 ─────────────────────────────────────

def run_llm_assertions_for_benchmark(
    content: str,
    benchmark_id: str,
    scenario: str | None = None,
    provider: str = "moonshot"
) -> dict:
    """对一个 benchmark 的所有 llm 类断言批量执行"""
    assertions_data = load_assertions(benchmark_id)

    if benchmark_id == "b2":
        if not scenario:
            raise ValueError(
                "B2 benchmark requires --scenario argument. "
                "Valid values: b2b / consumer / internal"
            )
        valid_scenarios = list(assertions_data.get("scenarios", {}).keys())
        if scenario not in assertions_data.get("scenarios", {}):
            raise ValueError(
                f"Unknown scenario '{scenario}' for B2. "
                f"Valid: {valid_scenarios}"
            )
        assertions = assertions_data["scenarios"][scenario]["assertions"]

    elif benchmark_id in ("b1", "b3"):
        assertions = assertions_data["assertions"]

    else:
        assertions = assertions_data.get("assertions", [])

    llm_assertions = [a for a in assertions if a.get("method") == "llm"]
    results = [run_llm_assertion(content, a, provider) for a in llm_assertions]

    llm_score = sum(r["score"] for r in results)
    llm_max = sum(r["max_score"] for r in results)

    return {
        "results": results,
        "llm_score": round(llm_score, 2),
        "llm_max_score": llm_max
    }
