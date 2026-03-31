from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv
load_dotenv()

from evaluators.assertion_checker import load_assertions

JUDGE_SYSTEM_PROMPT = """你是一个严格的产品文档评估专家。
你的任务是批量判断给定的文档内容是否满足多个断言条件。

规则：
1. 只返回 JSON 数组格式，不要有任何其他文字
2. 数组中每个元素对应一个断言的判断结果
3. confidence 范围：满足 0.7-1.0，不满足 0.0-0.3，部分满足 0.4-0.6
4. 判断要基于文档实际内容，不要推测未写出的内容
5. 如果文档内容标注为部分样本，请基于可见内容判断，不要因内容不完整而降低 confidence
"""


def _sample_content(content: str, max_chars: int = 3000) -> tuple[str, bool]:
    """对超长内容进行首尾采样"""
    if len(content) <= max_chars:
        return content, False
    head = content[:1200]
    tail = content[-800:]
    return f"{head}\n...[中间省略]...\n{tail}", True


def _build_batch_judge_prompt(content: str, assertions: list[dict]) -> str:
    """构建批量评估 prompt，一次调用评估所有 llm 断言"""
    sample, is_sampled = _sample_content(content)

    sampling_note = ""
    if is_sampled:
        sampling_note = (
            "\n【注意】文档较长，以下仅显示首尾部分。"
            "请基于可见内容判断，不要因内容不完整而降低 confidence。\n"
        )

    assertions_text = "\n".join([
        f"{i+1}. [ID:{a['id']}] {a['check']}"
        for i, a in enumerate(assertions)
    ])

    return f"""请批量判断以下文档是否满足各个断言条件。

【断言列表】
{assertions_text}
{sampling_note}
【文档内容】
{sample}

请返回 JSON 数组，数组长度必须与断言数量相同，顺序一一对应：
[
  {{"id": "断言ID", "passed": true或false, "confidence": 0到1的浮点数, "reason": "理由(10字以内)"}},
  ...
]

只返回 JSON 数组，不要有任何其他文字。"""


def _parse_batch_judge_response(raw: str, assertions: list[dict]) -> list[dict]:
    """解析批量评估响应，处理各种格式异常"""
    raw = raw.strip()

    # 提取 JSON 数组
    json_match = re.search(r'\[.*\]', raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)

    try:
        results = json.loads(raw)
        if not isinstance(results, list):
            raise ValueError("Response is not a list")

        # 验证并标准化每个结果
        parsed = []
        for i, item in enumerate(results):
            if i >= len(assertions):
                break
            parsed.append({
                "id": item.get("id", assertions[i]["id"]),
                "passed": bool(item.get("passed", False)),
                "confidence": float(item.get("confidence", 0.0)),
                "reason": str(item.get("reason", ""))[:100]
            })

        # 如果返回数量不足，补充失败结果
        while len(parsed) < len(assertions):
            i = len(parsed)
            parsed.append({
                "id": assertions[i]["id"],
                "passed": False,
                "confidence": 0.0,
                "reason": "Parse error: missing result"
            })

        return parsed

    except (json.JSONDecodeError, ValueError):
        # 解析完全失败，返回全部失败
        return [
            {
                "id": a["id"],
                "passed": False,
                "confidence": 0.0,
                "reason": "Parse error"
            }
            for a in assertions
        ]


async def run_llm_assertions_for_benchmark(
    content: str,
    benchmark_id: str,
    scenario: str | None = None
) -> dict:
    """
    批量执行所有 llm 类断言（一次 Claude API 调用）

    使用 Claude 作为 judge 评估 Kimi 生成的 PRD，
    避免用同一个模型自我评估的偏差。

    Returns:
        {results: [...], llm_score, llm_max_score}
    """
    import anthropic

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

    if not llm_assertions:
        return {"results": [], "llm_score": 0.0, "llm_max_score": 0}

    # 防御性检查
    valid_assertions = []
    for a in llm_assertions:
        if "id" not in a or "check" not in a:
            continue
        valid_assertions.append(a)

    if not valid_assertions:
        return {"results": [], "llm_score": 0.0, "llm_max_score": 0}

    # 构建批量 prompt
    prompt = _build_batch_judge_prompt(content, valid_assertions)

    # 调用 Claude 作为 judge
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. "
            "Please add it to your .env file."
        )

    client = anthropic.Anthropic(api_key=api_key)

    # 最多重试 3 次
    last_error = None
    raw = ""
    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                temperature=0.1,  # judge 用低温度，结果更稳定
                system=JUDGE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                timeout=60
            )
            raw = response.content[0].text if response.content else "[]"
            break
        except Exception as e:
            last_error = e
            if attempt < 2:
                import asyncio
                await asyncio.sleep(2 ** attempt)

    if not raw and last_error:
        raise last_error

    # 解析结果
    judgments = _parse_batch_judge_response(raw, valid_assertions)

    # 计算得分
    results = []
    for judgment, assertion in zip(judgments, valid_assertions):
        points = assertion.get("points", 2)
        confidence = judgment["confidence"]
        score = round(points * confidence, 2)

        results.append({
            "id": judgment["id"],
            "type": assertion.get("type", "completeness"),
            "method": "llm",
            "passed": judgment["passed"],
            "confidence": confidence,
            "score": score,
            "max_score": points,
            "reason": judgment["reason"]
        })

    llm_score = sum(r["score"] for r in results)
    llm_max = sum(r["max_score"] for r in results)

    return {
        "results": results,
        "llm_score": round(llm_score, 2),
        "llm_max_score": llm_max
    }
