"""在独立子进程中执行用户代码并返回结构化结果。

本脚本只负责“运行一次函数调用”，由 app/executor.py 以子进程方式启动。
注意：这是进程级隔离，不是容器级安全边界，详见 README 的“安全边界说明”。
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import traceback
from contextlib import redirect_stdout, redirect_stderr


class BlockedImportFinder:
    """best-effort 阻断常见网络模块导入，不能替代容器隔离。"""

    BLOCKED = {"socket", "urllib", "http", "requests", "ftplib", "smtplib", "telnetlib", "asyncio"}

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in self.BLOCKED:
            raise ImportError(f"评测环境已禁用网络相关模块: {fullname}")
        return None


def make_json_safe(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple, set, frozenset)):
        return [make_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): make_json_safe(v) for k, v in value.items()}
    return {"__repr__": repr(value)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", required=True)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--args", required=False, default=None)
    parser.add_argument("--args-file", required=False, default=None)
    parser.add_argument("--timeout-ms", type=int, default=2000)
    opts = parser.parse_args()

    sys.meta_path.insert(0, BlockedImportFinder())
    started = time.perf_counter()
    stdout = io.StringIO()
    stderr = io.StringIO()
    result = {
        "ok": False,
        "value": None,
        "error": "",
        "error_type": "",
        "stdout": "",
        "stderr": "",
        "runtime_ms": 0,
    }
    try:
        code = open(opts.code, "r", encoding="utf-8").read()
        namespace = {"__name__": "__submission__", "__file__": opts.code}
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(compile(code, "<submission>", "exec"), namespace)
            func = namespace.get(opts.entry)
            if not callable(func):
                raise NameError(f"未找到可调用入口函数: {opts.entry}()")
            call_args = json.loads(open(opts.args_file, "r", encoding="utf-8").read() if opts.args_file else opts.args)
            if not isinstance(call_args, list):
                raise TypeError("--args 必须是 JSON 数组")
            value = func(*call_args)
            result["value"] = make_json_safe(value)
            result["ok"] = True
    except Exception as exc:  # 用户代码异常必须转成结构化结果
        result["error"] = str(exc)
        result["error_type"] = type(exc).__name__
        result["traceback"] = traceback.format_exc(limit=8)
    finally:
        result["runtime_ms"] = int((time.perf_counter() - started) * 1000)
        result["stdout"] = stdout.getvalue()[:4000]
        result["stderr"] = stderr.getvalue()[:4000]
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
