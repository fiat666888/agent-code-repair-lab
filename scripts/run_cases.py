"""项目 C：真实执行 10 个代码 Bug 修复实验。

设计原则：
- 不伪造任何模型调用记录或测试结果。
- 所有 pre_fix_results / post_fix_results 均由本仓库自带的
  executor/run_case.py 在独立子进程中真实运行原始代码与修复代码后生成。
- 复用评测隔离层（Windows Job Object 已验证可用），本仓库已内置执行器，可独立运行。
"""
from __future__ import annotations

import glob
import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent          # agent-code-repair-lab
CASES_DIR = PROJECT_ROOT / "cases"
LOG_PATH = PROJECT_ROOT / "execution_log.md"

# 使用本仓库自带的独立子进程执行器（与 CodeEval Lab 同源）
sys.path.insert(0, str(PROJECT_ROOT / "executor"))
from executor import run_case  # noqa: E402

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    line = f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {message}"
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)


def detect_entry(code: str) -> str:
    """从顶层 def 中推断入口函数（类方法缩进，不会被匹配）。"""
    matches = re.findall(r"^def\s+(\w+)\s*\(", code, flags=re.MULTILINE)
    if not matches:
        raise ValueError("未找到顶层入口函数")
    return matches[-1]


def values_equal(actual, expected) -> bool:
    """结构化值的严格比较（数据均来自 JSON，可直接比较）。"""
    return actual == expected


def run_side(code: str, entry: str, test_cases: list) -> dict:
    """真实执行一侧代码（原始或修复），逐用例比对期望。"""
    rows = []
    for test in test_cases:
        name = test["name"]
        args = test.get("args", [])
        expected = test.get("expected")
        timeout_ms = int(test.get("timeout_ms", 2000))
        result = run_case(code, entry, args, timeout_ms)
        actual = result.get("value")
        passed = bool(result.get("ok")) and values_equal(actual, expected)
        rows.append({
            "name": name,
            "args": args,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "ok": bool(result.get("ok")),
            "error": result.get("error", ""),
            "error_type": result.get("error_type", ""),
            "timed_out": bool(result.get("timed_out")),
            "runtime_ms": result.get("runtime_ms", 0),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
        })
    passed_count = sum(1 for r in rows if r["passed"])
    total = len(rows)
    return {
        "passed": passed_count,
        "total": total,
        "all_passed": total > 0 and passed_count == total,
        "note": "由 scripts/run_cases.py 调用 executor/executor.py（与 CodeEval Lab 同源） 的 run_case 在独立子进程真实执行后生成",
        "cases": rows,
    }


def result_table(rows: list) -> list[str]:
    lines = [
        "| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |",
        "| --- | --- | --- | :---: | --- | :---: | ---: |",
    ]
    for r in rows:
        exp = json.dumps(r["expected"], ensure_ascii=False)
        act = json.dumps(r["actual"], ensure_ascii=False)
        err = (r["error"] or "—").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {r['name']} | `{exp}` | `{act}` | {'是' if r['passed'] else '否'} | "
            f"{err} | {'是' if r['timed_out'] else '否'} | {r['runtime_ms']} |"
        )
    return lines


def render_ai_process(process) -> list[str]:
    if isinstance(process, str):
        return [process]
    lines = []
    if process.get("performed_by"):
        lines += [f"- 执行者：{process['performed_by']}", ""]
    for key, title in (
        ("analysis_steps", "分析步骤"),
        ("fix_steps", "修复步骤"),
        ("retest_steps", "复测步骤"),
    ):
        lines.append(f"**{title}**")
        lines.append("")
        for step in process.get(key, []):
            lines.append(f"1. {step}")
        lines.append("")
    lines.append(f"> {process.get('transcript_statement', '')}")
    return lines


def case_to_markdown(case: dict) -> str:
    pre = case["pre_fix_results"]
    post = case["post_fix_results"]
    lines = [
        f"# 案例 {case['id']}：{case['title']}", "",
        "## 1. 编号", "",
        f"- 编号：{case['id']}　类别：{case['category']}", "",
        "## 2. 问题描述", "",
        case["problem_description"], "",
        "## 3. 原始代码", "",
        "```python", case["original_code"].rstrip(), "```", "",
        "## 4. Bug 原因", "",
        case["bug_cause"], "",
        "## 5. 修复要求", "",
        case["fix_requirement"], "",
        "## 6. AI 修复过程", "",
    ]
    lines += render_ai_process(case["ai_repair_process"])
    lines += ["", "## 7. 修复后代码", "",
              "```python", case["fixed_code"].rstrip(), "```", "",
              "## 8. 测试用例", "",
              "| 用例 | 输入参数(args) | 期望(expected) | 超时(ms) |",
              "| --- | --- | --- | ---: |"]
    for test in case["test_cases"]:
        lines.append(
            f"| {test['name']} | `{json.dumps(test.get('args', []), ensure_ascii=False)}` | "
            f"`{json.dumps(test.get('expected'), ensure_ascii=False)}` | {test.get('timeout_ms', 2000)} |"
        )
    lines += ["", "## 9. 修复前结果（原始代码真实执行）", "",
              f"- 通过：{pre['passed']}/{pre['total']}　全部通过：{'是' if pre['all_passed'] else '否'}", ""]
    lines += result_table(pre["cases"])
    lines += ["", "## 10. 修复后结果（修复代码真实执行）", "",
              f"- 通过：{post['passed']}/{post['total']}　全部通过：{'是' if post['all_passed'] else '否'}", ""]
    lines += result_table(post["cases"])
    lines += ["", "## 11. 人工代码审查", "", case["manual_review"], "",
              "## 12. 最终评价", "", case["final_evaluation"], ""]
    return "\n".join(lines) + "\n"


def main_run() -> None:
    paths = sorted(glob.glob(str(CASES_DIR / "case_*.json")))
    log(f"项目 C 开始执行：共发现 {len(paths)} 个案例文件；执行器 isolation 复用 executor/executor.py（与 CodeEval Lab 同源）")
    summary_rows = []
    total_pre_passed = total_post_passed = total_cases = 0

    for path in paths:
        case = json.loads(Path(path).read_text(encoding="utf-8"))
        entry = detect_entry(case["fixed_code"])
        pre_fix = run_side(case["original_code"], entry, case["test_cases"])
        post_fix = run_side(case["fixed_code"], entry, case["test_cases"])

        case["pre_fix_results"] = pre_fix
        case["post_fix_results"] = post_fix
        Path(path).write_text(
            json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        md_name = Path(path).stem + ".md"
        (CASES_DIR / md_name).write_text(case_to_markdown(case), encoding="utf-8")

        failed_pre = [r["name"] for r in pre_fix["cases"] if not r["passed"]]
        failed_post = [r["name"] for r in post_fix["cases"] if not r["passed"]]
        status = "OK" if pre_fix["passed"] < pre_fix["total"] and post_fix["all_passed"] else "CHECK"
        log(f"{case['id']} [{status}] {case['category']} {case['title']} | 入口 {entry}() | "
            f"原始 {pre_fix['passed']}/{pre_fix['total']} 修复 {post_fix['passed']}/{post_fix['total']} | "
            f"原始失败用例={failed_pre} | 修复失败用例={failed_post}")

        total_pre_passed += pre_fix["passed"]
        total_post_passed += post_fix["passed"]
        total_cases += pre_fix["total"]
        summary_rows.append({
            "id": case["id"], "category": case["category"], "title": case["title"],
            "pre": pre_fix, "post": post_fix,
        })

    categories = "、".join(r["category"] for r in summary_rows)
    lines = [
        "# 项目 C · Agent Code Repair Lab 真实执行汇总", "",
        f"生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}", "",
        "所有结果均由 `executor/executor.py（与 CodeEval Lab 同源）` 的 `run_case` 在独立子进程中真实运行原始代码与修复代码后生成，",
        "记录包含实际返回值、错误信息、是否超时与真实耗时（毫秒）。未伪造模型调用记录或测试结果。", "",
        "## 10 类覆盖", "",
        categories, "",
        f"## 总体统计", "",
        f"- 用例总数：{total_cases}",
        f"- 原始代码累计通过：{total_pre_passed}/{total_cases}",
        f"- 修复代码累计通过：{total_post_passed}/{total_cases}", "",
        "## 逐案例结果", "",
        "| # | 类别 | 题目 | 修复前 | 修复后 | 结论 |",
        "| ---: | --- | --- | ---: | ---: | --- |",
    ]
    for r in summary_rows:
        conclusion = "原始存在失败用例，修复后全部通过" if (
            r["pre"]["passed"] < r["pre"]["total"] and r["post"]["all_passed"]) else "需复核（见日志与案例文档）"
        lines.append(
            f"| {r['id']} | {r['category']} | {r['title']} | "
            f"{r['pre']['passed']}/{r['pre']['total']} | {r['post']['passed']}/{r['post']['total']} | {conclusion} |"
        )
    (CASES_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"项目 C 执行完成：用例总数 {total_cases}，原始通过 {total_pre_passed}，修复通过 {total_post_passed}；日志 {LOG_PATH}")


if __name__ == "__main__":
    main_run()
