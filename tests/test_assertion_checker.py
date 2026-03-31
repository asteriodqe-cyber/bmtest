from __future__ import annotations

import pytest
from evaluators.assertion_checker import (
    check_keyword_presence,
    check_keyword_absence,
    check_section_order,
    run_rule_assertion,
    extract_section_position
)


# ── check_keyword_presence ────────────────────────────────

def test_keyword_presence_found():
    assert check_keyword_presence("这份文档包含背景章节", ["背景", "Background"]) is True

def test_keyword_presence_not_found():
    assert check_keyword_presence("这份文档没有相关内容", ["背景", "Background"]) is False

def test_keyword_presence_case_insensitive():
    assert check_keyword_presence("This has BACKGROUND section", ["background"]) is True

def test_keyword_presence_empty_content():
    assert check_keyword_presence("", ["背景"]) is False


# ── check_keyword_absence ─────────────────────────────────

def test_keyword_absence_not_present():
    assert check_keyword_absence("这是普通内容", ["病毒式传播", "裂变"]) is True

def test_keyword_absence_present():
    assert check_keyword_absence("我们要做病毒式传播", ["病毒式传播", "裂变"]) is False


# ── check_section_order ───────────────────────────────────

def test_section_order_correct():
    content = "## 背景\n内容\n## 用户故事\n内容"
    assert check_section_order(content, ["背景"], ["用户故事"]) is True

def test_section_order_incorrect():
    content = "## 用户故事\n内容\n## 背景\n内容"
    assert check_section_order(content, ["背景"], ["用户故事"]) is False

def test_section_order_missing_first():
    content = "## 用户故事\n内容"
    assert check_section_order(content, ["背景"], ["用户故事"]) is False

def test_section_order_missing_second():
    content = "## 背景\n内容"
    assert check_section_order(content, ["背景"], ["用户故事"]) is False


# ── run_rule_assertion ────────────────────────────────────

def test_rule_assertion_structural_pass():
    content = "## 背景\n这是背景内容"
    assertion = {
        "id": "test_01",
        "type": "structural",
        "method": "rule",
        "check": "输出包含'背景'或'Background'章节",
        "points": 1
    }
    result = run_rule_assertion(content, assertion)
    assert result["passed"] is True
    assert result["score"] == 1

def test_rule_assertion_structural_fail():
    content = "## 目标\n这是目标内容"
    assertion = {
        "id": "test_02",
        "type": "structural",
        "method": "rule",
        "check": "输出包含'背景'或'Background'章节",
        "points": 1
    }
    result = run_rule_assertion(content, assertion)
    assert result["passed"] is False
    assert result["score"] == 0

def test_rule_assertion_absence_pass():
    content = "## 目标\n提升效率"
    assertion = {
        "id": "test_03",
        "type": "content_absence",
        "method": "rule",
        "check": "不包含'病毒式传播'或'裂变'",
        "points": 1
    }
    result = run_rule_assertion(content, assertion)
    assert result["passed"] is True

def test_rule_assertion_missing_field():
    assertion = {"id": "test_04", "type": "structural", "method": "rule", "points": 1}
    result = run_rule_assertion("内容", assertion)
    assert result["passed"] is False
    assert result["type"] == "error"
    assert "Missing required field" in result["reason"]

def test_rule_assertion_ordering_pass():
    content = "## 背景\n内容\n## 验收标准\n内容"
    assertion = {
        "id": "test_05",
        "type": "ordering",
        "method": "rule",
        "check": "'背景'章节出现在'验收标准'章节之前",
        "points": 1
    }
    result = run_rule_assertion(content, assertion)
    assert result["passed"] is True
