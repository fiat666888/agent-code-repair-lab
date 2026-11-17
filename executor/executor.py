"""代码执行隔离层。

优先级：Docker 容器 > Windows Job Object / POSIX rlimit 的独立子进程 > 仅超时子进程。
当前环境没有 Docker，因此使用进程级隔离，并在 capabilities() 中如实标注限制。
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
RUNNER = APP_DIR / "runner.py"
MEMORY_LIMIT_MB = int(os.environ.get("CODEEVAL_MEMORY_MB", "256"))
CPU_LIMIT_SECONDS = float(os.environ.get("CODEEVAL_CPU_SECONDS", "5"))

_IS_WINDOWS = platform.system() == "Windows"
_job_api = None


def _windows_job_api():
    global _job_api
    if _job_api is not None:
        return _job_api

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class BasicLimit(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
        )]

    class ExtendedLimit(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimit),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.restype = wintypes.DWORD

    _job_api = {
        "k32": kernel32, "BasicLimit": BasicLimit, "ExtendedLimit": ExtendedLimit,
        "JOB_OBJECT_LIMIT_JOB_TIME": 0x00000004,
        "JOB_OBJECT_LIMIT_PROCESS_MEMORY": 0x00000100,
        "JOB_OBJECT_LIMIT_JOB_MEMORY": 0x00000200,
        "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE": 0x00002000,
    }
    return _job_api


def _create_job(cpu_seconds: float):
    api = _windows_job_api()
    k32 = api["k32"]
    job = k32.CreateJobObjectW(None, None)
    if not job or job == -1:
        return None, "创建 Job Object 失败"
    info = api["ExtendedLimit"]()
    basic = info.BasicLimitInformation
    basic.LimitFlags = (
        api["JOB_OBJECT_LIMIT_JOB_TIME"]
        | api["JOB_OBJECT_LIMIT_PROCESS_MEMORY"]
        | api["JOB_OBJECT_LIMIT_JOB_MEMORY"]
        | api["JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE"]
    )
    basic.PerJobUserTimeLimit = int(max(0.2, cpu_seconds) * 10_000_000)
    info.ProcessMemoryLimit = MEMORY_LIMIT_MB * 1024 * 1024
    info.JobMemoryLimit = MEMORY_LIMIT_MB * 2 * 1024 * 1024
    ok = k32.SetInformationJobObject(job, 9, ctypes_byref(info), ctypes_sizeof(info))
    if not ok:
        k32.CloseHandle(job)
        return None, "设置 Job Object 限制失败"
    return job, None


def ctypes_byref(obj):
    import ctypes
    return ctypes.byref(obj)


def ctypes_sizeof(obj):
    import ctypes
    return ctypes.sizeof(obj)


def _posix_limits(cpu_seconds: int, memory_bytes: int):
    import resource

    def apply():
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    return apply


def run_case(code: str, entry: str, args: list, timeout_ms: int = 2000) -> dict:
    """在隔离进程中执行单个测试用例，返回结构化结果。"""
    started = time.perf_counter()
    timeout_s = max(0.2, min(timeout_ms, 20000) / 1000.0)
    job = None
    proc = None
    job_applied = False
    job_error = ""
    result = {
        "ok": False, "value": None, "error": "", "error_type": "",
        "traceback": "", "stdout": "", "stderr": "", "runtime_ms": 0,
        "timed_out": False, "job_applied": False, "job_error": "",
    }

    with tempfile.TemporaryDirectory(prefix="codeeval_") as tmp:
        code_path = Path(tmp) / "submission.py"
        code_path.write_text(code, encoding="utf-8")
        args_path = Path(tmp) / "args.json"
        args_path.write_text(json.dumps(args, ensure_ascii=False), encoding="utf-8")
        cmd = [sys.executable, str(RUNNER), "--code", str(code_path),
               "--entry", str(entry), "--args-file", str(args_path),
               "--timeout-ms", str(int(timeout_ms))]
        env = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
               "PYTHONIOENCODING": "utf-8", "CODEEVAL_CHILD": "1"}

        creationflags = 0
        preexec_fn = None
        if _IS_WINDOWS:
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            job, job_error = _create_job(max(timeout_s, CPU_LIMIT_SECONDS))
        elif hasattr(os, "setsid"):
            preexec_fn = _posix_limits(max(1, int(timeout_s) + 1), MEMORY_LIMIT_MB * 1024 * 1024)

        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", env=env,
                cwd=tmp, creationflags=creationflags, preexec_fn=preexec_fn,
            )
            if _IS_WINDOWS:
                api = _windows_job_api()
                handle = getattr(proc, "_handle", None)
                if job and handle is not None:
                    assigned = api["k32"].AssignProcessToJobObject(job, wintypes_handle(handle))
                    if assigned:
                        job_applied = True
                    else:
                        job_error = f"AssignProcessToJobObject 失败，错误码 {ctypes_get_last_error()}"
            out, err = proc.communicate(timeout=timeout_s)
            try:
                payload = json.loads(out.strip().splitlines()[-1])
                result.update({k: payload.get(k, result[k]) for k in (
                    "ok", "value", "error", "error_type", "traceback", "stdout", "stderr", "runtime_ms"
                )})
            except (ValueError, IndexError):
                result["error"] = "评测子进程未返回合法 JSON"
                result["error_type"] = "RunnerProtocolError"
                result["stderr"] = (err or out or "")[:2000]
        except subprocess.TimeoutExpired:
            result["timed_out"] = True
            result["error_type"] = "TimeoutError"
            result["error"] = f"执行超时（超过 {int(timeout_s * 1000)} ms）"
            _kill_process(proc, job)
            try:
                out, err = proc.communicate(timeout=2)
            except Exception:
                out, err = "", ""
            result["stderr"] = (err or out or "")[:1000]
        except Exception as exc:
            result["error"] = f"评测器启动失败: {exc}"
            result["error_type"] = type(exc).__name__
            _kill_process(proc, job)
        finally:
            if job is not None and _IS_WINDOWS:
                _windows_job_api()["k32"].CloseHandle(job)
            result["runtime_ms"] = result["runtime_ms"] or int((time.perf_counter() - started) * 1000)
            result["job_applied"] = job_applied
            result["job_error"] = job_error
    return result


def wintypes_handle(value):
    import ctypes
    from ctypes import wintypes
    if isinstance(value, wintypes.HANDLE):
        return value
    return wintypes.HANDLE(value)


def ctypes_get_last_error():
    import ctypes
    return ctypes.get_last_error()


def _kill_process(proc, job) -> None:
    if job is not None and _IS_WINDOWS:
        try:
            _windows_job_api()["k32"].TerminateJobObject(job, 1)
            return
        except Exception:
            pass
    if proc is not None:
        try:
            proc.kill()
        except Exception:
            pass


def docker_available() -> bool:
    exe = shutil.which("docker")
    if not exe:
        return False
    try:
        out = subprocess.run([exe, "info", "--format", "{{.ServerVersion}}"],
                             capture_output=True, text=True, timeout=3)
        return out.returncode == 0
    except Exception:
        return False


def capabilities() -> dict:
    docker = docker_available()
    if docker:
        mode = "docker-available-not-enabled"
        isolation = "未启用容器；当前仍使用进程级隔离。Docker 配置文件已随项目提供。"
    elif _IS_WINDOWS:
        probe = _create_job(CPU_LIMIT_SECONDS)
        ok = probe[0] is not None
        if probe[0] is not None:
            _windows_job_api()["k32"].CloseHandle(probe[0])
        mode = "process-job-object" if ok else "process-timeout-only"
        isolation = ("独立子进程 + Windows Job Object（CPU/内存/进程树限制）"
                     if ok else "独立子进程 + 超时限制（Job Object 不可用）")
    else:
        mode = "process-rlimit"
        isolation = "独立子进程 + POSIX rlimit（CPU/内存/文件大小限制）"

    return {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "docker_available": docker,
        "isolation_mode": mode,
        "isolation_summary": isolation,
        "memory_limit_mb": MEMORY_LIMIT_MB,
        "cpu_limit_seconds": CPU_LIMIT_SECONDS,
        "security_notice": (
            "重要：当前不是容器隔离，进程级隔离不构成强安全边界。"
            "恶意代码仍可能访问本机文件或通过底层系统调用绕过限制。"
            "仅用于可信或半可信代码的教学评测；请勿在公网暴露本服务。"
        ),
    }
