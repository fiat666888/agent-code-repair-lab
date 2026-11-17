# 案例 C06：重复元素检测：O(n²) 双重循环导致大输入超时

## 1. 编号

- 编号：C06　类别：算法效率问题

## 2. 问题描述

函数 has_duplicate(size) 先构造 list(range(size))（天然无重复），再判断是否含重复元素。原始代码使用双重嵌套循环两两比较，时间复杂度 O(n²)；在大输入下会远超超时限制。需改为 O(n) 的集合去重判断。

## 3. 原始代码

```python
def has_duplicate(size):
    items = list(range(int(size)))
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j]:
                return True
    return False
```

## 4. Bug 原因

采用暴力双重循环逐对比较，时间复杂度 O(n²)。当 size=50000 时需约 12.5 亿次比较，在超时限制内无法完成，导致 TimeoutError。

## 5. 修复要求

利用集合去重后比较长度：len(set(items)) != len(items)，将复杂度降为 O(n)，并保证大输入在超时内完成。

## 6. AI 修复过程

- 执行者：本次由 AI 辅助完成定位与修复（CodeBuddy Code 执行分析与改写）

**分析步骤**

1. 分析原始算法为双重循环，估算 n=50000 时比较次数约 n(n-1)/2，判定必然超时。
1. 确认题目要求的是「是否存在重复」这一判定问题，可用集合去重一次完成。
1. 确认 set 构造与长度比较均为 O(n)，满足大输入约束。

**修复步骤**

1. 移除嵌套循环，改为 len(set(items)) != len(items) 的判定。
1. 保留 items 构造与函数签名、返回布尔值不变。

**复测步骤**

1. 通过真实独立子进程运行小输入（size=10）与大输入（size=50000，timeout 1500ms）。
1. 记录原始代码在大输入上的 timed_out 与 runtime_ms，确认其失败。
1. 确认修复代码两个用例均在超时内通过。

> 未保存模型对话原文，不提供虚构的对话记录。

## 7. 修复后代码

```python
def has_duplicate(size):
    items = list(range(int(size)))
    return len(set(items)) != len(items)
```

## 8. 测试用例

| 用例 | 输入参数(args) | 期望(expected) | 超时(ms) |
| --- | --- | --- | ---: |
| small_no_duplicate | `[10]` | `false` | 1500 |
| large_input_50k | `[50000]` | `false` | 1500 |

## 9. 修复前结果（原始代码真实执行）

- 通过：1/2　全部通过：否

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| small_no_duplicate | `false` | `false` | 是 | — | 否 | 2 |
| large_input_50k | `false` | `null` | 否 | 执行超时（超过 1500 ms） | 是 | 1514 |

## 10. 修复后结果（修复代码真实执行）

- 通过：2/2　全部通过：是

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| small_no_duplicate | `false` | `false` | 是 | — | 否 | 2 |
| large_input_50k | `false` | `false` | 是 | — | 否 | 6 |

## 11. 人工代码审查

人工审查确认：集合去重判定语义与「是否存在重复」完全等价；复杂度由 O(n²) 降为 O(n)；未改变输入构造与返回类型。属于针对性最小改动。

## 12. 最终评价

修复有效。原始代码在小输入通过、大输入（50000）超时失败（失败 1/2），修复代码 2/2 通过。大输入加超时限制真实体现了复杂度差异。

