# 案例 C09：异常路径遗漏 release 导致资源泄漏

## 1. 编号

- 编号：C09　类别：资源管理问题

## 2. 问题描述

函数 process_batch(items, fail_on_bad) 使用可观测的模拟资源池 ResourcePool 记录每次 acquire/release。处理到 'bad' 元素时会提前中断。原始代码在中断路径上直接 break，没有释放刚获取的资源，造成泄漏。需真实运行比较 acquire/release 计数。

## 3. 原始代码

```python
class ResourcePool:
    def __init__(self):
        self.acquired = 0
        self.released = 0

    def acquire(self):
        self.acquired += 1
        return 'token-{}'.format(self.acquired)

    def release(self, token):
        self.released += 1


def process_batch(items, fail_on_bad=True):
    pool = ResourcePool()
    error = None
    for item in items:
        token = pool.acquire()
        if fail_on_bad and item == 'bad':
            error = 'bad item'
            break
        pool.release(token)
    return {'error': error, 'acquired': pool.acquired, 'released': pool.released, 'leaked': pool.acquired - pool.released}
```

## 4. Bug 原因

资源释放语句位于普通路径末尾，遇到 'bad' 提前 break 时跳过 release，使得 acquired 比 released 多 1，产生可观测泄漏（leaked=1）。

## 5. 修复要求

用 try/finally 包裹获取资源后的处理逻辑，确保无论正常结束还是中断，当前 token 都被 release，使 leaked 恒为 0。

## 6. AI 修复过程

- 执行者：本次由 AI 辅助完成定位与修复（CodeBuddy Code 执行分析与改写）

**分析步骤**

1. 发现 acquire 后立即判断 item，命中 'bad' 时 break，跳过循环体末尾的 release。
1. 确认这是提前退出路径上的资源泄漏，可用返回的 leaked 字段观测。
1. 判断 try/finally 能覆盖正常与中断两条路径，且不改变业务结果。

**修复步骤**

1. 在 token = pool.acquire() 之后用 try 包裹判断分支。
1. 在 finally 中调用 pool.release(token)，保证每次 acquire 都对应一次 release。

**复测步骤**

1. 通过真实独立子进程运行正常批次与含 'bad' 的批次两组用例。
1. 读取返回的 acquired/released/leaked 实际值并比对 expected。
1. 确认原始代码在中断用例 leaked=1（失败）、修复代码 leaked=0 且全部通过。

> 未保存模型对话原文，不提供虚构的对话记录。

## 7. 修复后代码

```python
class ResourcePool:
    def __init__(self):
        self.acquired = 0
        self.released = 0

    def acquire(self):
        self.acquired += 1
        return 'token-{}'.format(self.acquired)

    def release(self, token):
        self.released += 1


def process_batch(items, fail_on_bad=True):
    pool = ResourcePool()
    error = None
    for item in items:
        token = pool.acquire()
        try:
            if fail_on_bad and item == 'bad':
                error = 'bad item'
                break
        finally:
            pool.release(token)
    return {'error': error, 'acquired': pool.acquired, 'released': pool.released, 'leaked': pool.acquired - pool.released}
```

## 8. 测试用例

| 用例 | 输入参数(args) | 期望(expected) | 超时(ms) |
| --- | --- | --- | ---: |
| normal_no_bad | `[["ok", "ok"], true]` | `{"error": null, "acquired": 2, "released": 2, "leaked": 0}` | 2000 |
| leak_on_bad | `[["ok", "bad", "ok"], true]` | `{"error": "bad item", "acquired": 2, "released": 2, "leaked": 0}` | 2000 |

## 9. 修复前结果（原始代码真实执行）

- 通过：1/2　全部通过：否

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| normal_no_bad | `{"error": null, "acquired": 2, "released": 2, "leaked": 0}` | `{"error": null, "acquired": 2, "released": 2, "leaked": 0}` | 是 | — | 否 | 2 |
| leak_on_bad | `{"error": "bad item", "acquired": 2, "released": 2, "leaked": 0}` | `{"error": "bad item", "acquired": 2, "released": 1, "leaked": 1}` | 否 | — | 否 | 2 |

## 10. 修复后结果（修复代码真实执行）

- 通过：2/2　全部通过：是

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| normal_no_bad | `{"error": null, "acquired": 2, "released": 2, "leaked": 0}` | `{"error": null, "acquired": 2, "released": 2, "leaked": 0}` | 是 | — | 否 | 2 |
| leak_on_bad | `{"error": "bad item", "acquired": 2, "released": 2, "leaked": 0}` | `{"error": "bad item", "acquired": 2, "released": 2, "leaked": 0}` | 是 | — | 否 | 2 |

## 11. 人工代码审查

人工审查确认：try/finally 精确覆盖每个 acquire 后的释放，业务返回值 error 与中断语义不变；模拟资源类真实记录计数，泄漏可被量化观测，非理论推演。

## 12. 最终评价

修复有效。原始代码在 leak_on_bad 用例返回 leaked=1（失败 1/2），修复代码两用例 leaked 均为 0，2/2 通过。真实体现了资源泄漏与修复。

