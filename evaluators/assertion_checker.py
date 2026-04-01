from __future__ import annotations

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent


# ── 断言文件加载 ──────────────────────────────────────────

def load_assertions(benchmark_id: str, version: str = "v1") -> dict:
    """
    加载对应 benchmark 的断言定义

    Args:
        benchmark_id: b1 / b2 / b3
        version:      v1（原版）或 v2（扩充关键词版），默认 v1
    """
    file_map = {
        "b1": {
            "v1": "benchmark/assertions/b1_structure.json",
            "v2": "benchmark/assertions/b1_structure_v2.json"
        },
        "b2": {
            "v1": "benchmark/assertions/b2_conditional.json",
            "v2": "benchmark/assertions/b2_conditional_v2.json"
        },
        "b3": {
            "v1": "benchmark/assertions/b3_orchestration.json",
            "v2": "benchmark/assertions/b3_orchestration_v2.json"
        }
    }

    if benchmark_id not in file_map:
        raise ValueError(f"Unknown benchmark_id: {benchmark_id}")

    version_map = file_map[benchmark_id]
    if version not in version_map:
        raise ValueError(
            f"Unknown version '{version}' for {benchmark_id}. "
            f"Valid: {list(version_map.keys())}"
        )

    path = BASE_DIR / version_map[version]
    if not path.exists():
        raise FileNotFoundError(f"Assertion file not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


# ── 基础检查工具 ──────────────────────────────────────────

def check_keyword_presence(content: str, keywords: list[str]) -> bool:
    """检查 content 是否包含关键词列表中的任意一个"""
    content_lower = content.lower()
    return any(kw.lower() in content_lower for kw in keywords)


def check_keyword_absence(content: str, keywords: list[str]) -> bool:
    """检查 content 是否不包含关键词列表中的任意一个（返回 True 表示通过）"""
    content_lower = content.lower()
    return not any(kw.lower() in content_lower for kw in keywords)


def extract_section_position(content: str, section_keywords: list[str]) -> int:
    """
    返回章节在文档中的位置（字符偏移量）
    找不到返回 -1
    """
    content_lower = content.lower()
    for kw in section_keywords:
        idx = content_lower.find(kw.lower())
        if idx != -1:
            return idx
    return -1


def check_section_order(
    content: str,
    first_keywords: list[str],
    second_keywords: list[str]
) -> bool:
    """检查 first 章节是否出现在 second 章节之前"""
    pos_first = extract_section_position(content, first_keywords)
    pos_second = extract_section_position(content, second_keywords)
    if pos_first == -1 or pos_second == -1:
        return False
    return pos_first < pos_second


# ── 关键词提取 ────────────────────────────────────────────

def _extract_keywords_from_check(check_text: str) -> list[str]:
    """
    从断言的 check 字段提取关键词
    格式：包含'A'或'B'或'C' → ['A', 'B', 'C']
    """
    keywords = re.findall(r"'([^']+)'", check_text)
    return keywords if keywords else [check_text]


def _check_ordering_from_text(content: str, check_text: str) -> tuple[bool, str]:
    """
    从 check 文本解析章节顺序断言
    格式："'A'章节出现在'B'章节之前"
    """
    keywords = re.findall(r"'([^']+)'", check_text)
    if len(keywords) < 2:
        return False, "Cannot parse ordering assertion"

    passed = check_section_order(content, [keywords[0]], [keywords[1]])
    reason = (
        f"'{keywords[0]}' appears before '{keywords[1]}'"
        if passed
        else f"'{keywords[0]}' does not appear before '{keywords[1]}'"
    )
    return passed, reason


# ── 单条 rule 断言执行 ────────────────────────────────────

def run_rule_assertion(content: str, assertion: dict) -> dict:
    """
    执行单条 rule 类断言
    返回 {id, type, method, passed, score, max_score, reason}
    """
    required_fields = ["id", "check"]
    for required_field in required_fields:
        if required_field not in assertion:
            return {
                "id": assertion.get("id", "unknown"),
                "type": "error",
                "method": "rule",
                "passed": False,
                "score": 0,
                "max_score": 0,
                "reason": f"Missing required field: {required_field}"
            }

    assertion_id = assertion["id"]
    check_text = assertion["check"]
    points = assertion.get("points", 1)
    assertion_type = assertion.get("type", "structural")

    passed = False
    reason = ""

    if assertion_type in ("structural", "content_presence", "depth", "step_existence"):
        keywords = _extract_keywords_from_check(check_text)
        passed = check_keyword_presence(content, keywords)
        reason = (
            f"Found keywords: {keywords}"
            if passed
            else f"Missing keywords: {keywords}"
        )

    elif assertion_type == "content_absence":
        keywords = _extract_keywords_from_check(check_text)
        passed = check_keyword_absence(content, keywords)
        reason = (
            "Absence check passed"
            if passed
            else f"Found unwanted keywords: {keywords}"
        )

    elif assertion_type == "ordering":
        passed, reason = _check_ordering_from_text(content, check_text)

    else:
        keywords = _extract_keywords_from_check(check_text)
        passed = check_keyword_presence(content, keywords)
        reason = f"Default check: {'passed' if passed else 'failed'}"

    return {
        "id": assertion_id,
        "type": assertion_type,
        "method": "rule",
        "passed": passed,
        "score": points if passed else 0,
        "max_score": points,
        "reason": reason
    }


# ── 批量 rule 断言执行 ────────────────────────────────────

def run_rule_assertions_for_benchmark(
    content: str,
    benchmark_id: str,
    scenario: str | None = None,
    version: str = "v1"
) -> dict:
    """
    对一个 benchmark 的所有 rule 类断言批量执行

    Args:
        content:      Agent 生成的文本内容
        benchmark_id: b1 / b2 / b3
        scenario:     B2 必须指定（b2b / consumer / internal）
        version:      断言版本，v1（原版）或 v2（扩充关键词版），默认 v1

    Returns:
        {results: [...], rule_score, rule_max_score}
    """
    assertions_data = load_assertions(benchmark_id, version)

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

    rule_assertions = [a for a in assertions if a.get("method") == "rule"]
    results = [run_rule_assertion(content, a) for a in rule_assertions]

    rule_score = sum(r["score"] for r in results)
    rule_max = sum(r["max_score"] for r in results)

    return {
        "results": results,
        "rule_score": rule_score,
        "rule_max_score": rule_max
    }
