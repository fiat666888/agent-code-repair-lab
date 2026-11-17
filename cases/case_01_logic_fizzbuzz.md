# 案例 C01：FizzBuzz 分支条件逻辑错误（or 误用为 and）

## 1. 编号

- 编号：C01　类别：逻辑错误

## 2. 问题描述

函数 fizzbuzz_value(n) 应对 3 的倍数返回 Fizz、5 的倍数返回 Buzz、同时是 3 和 5 的倍数返回 FizzBuzz，其余返回数字字符串。原始代码把「同时满足」写成了「满足其一」，导致 3 和 5 的倍数被错误归类为 FizzBuzz。

## 3. 原始代码

```python
def fizzbuzz_value(n):
    if n % 3 == 0 or n % 5 == 0:
        return "FizzBuzz"
    if n % 3 == 0:
        return "Fizz"
    if n % 5 == 0:
        return "Buzz"
    return str(n)
```

## 4. Bug 原因

第一个 if 使用逻辑或（or），使得任意满足 3 或 5 整除条件的数字都先命中 FizzBuzz 分支，后面的 Fizz/Buzz 分支成为死代码。应为逻辑与（and），或先判断 n % 15 == 0。

## 5. 修复要求

将第一个条件改为 n % 3 == 0 and n % 5 == 0，使 FizzBuzz 仅在同时整除时返回；保持其余分支不变。

## 6. AI 修复过程

- 执行者：本次由 AI 辅助完成定位与修复（CodeBuddy Code 执行分析与改写）

**分析步骤**

1. 阅读题目与原始代码，梳理四个返回分支的优先级。
1. 对照期望：3->Fizz、5->Buzz、15->FizzBuzz，定位首个 if 使用 or 导致分支覆盖错误。
1. 确认后续 Fizz/Buzz 分支因首个条件过宽而不可达。

**修复步骤**

1. 把首个条件由 or 修改为 and，缩小 FizzBuzz 的命中范围。
1. 保留其余分支与返回类型，避免引入额外行为变化。

**复测步骤**

1. 使用真实独立子进程执行原始代码与修复代码。
1. 逐用例比对实际返回值与 expected（3/5/15/7）。
1. 确认原始代码至少 1 个用例失败、修复代码全部通过。

> 未保存模型对话原文，不提供虚构的对话记录。

## 7. 修复后代码

```python
def fizzbuzz_value(n):
    if n % 3 == 0 and n % 5 == 0:
        return "FizzBuzz"
    if n % 3 == 0:
        return "Fizz"
    if n % 5 == 0:
        return "Buzz"
    return str(n)
```

## 8. 测试用例

| 用例 | 输入参数(args) | 期望(expected) | 超时(ms) |
| --- | --- | --- | ---: |
| three_only | `[3]` | `"Fizz"` | 2000 |
| five_only | `[5]` | `"Buzz"` | 2000 |
| both_three_and_five | `[15]` | `"FizzBuzz"` | 2000 |
| neither | `[7]` | `"7"` | 2000 |

## 9. 修复前结果（原始代码真实执行）

- 通过：2/4　全部通过：否

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| three_only | `"Fizz"` | `"FizzBuzz"` | 否 | — | 否 | 2 |
| five_only | `"Buzz"` | `"FizzBuzz"` | 否 | — | 否 | 2 |
| both_three_and_five | `"FizzBuzz"` | `"FizzBuzz"` | 是 | — | 否 | 2 |
| neither | `"7"` | `"7"` | 是 | — | 否 | 2 |

## 10. 修复后结果（修复代码真实执行）

- 通过：4/4　全部通过：是

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| three_only | `"Fizz"` | `"Fizz"` | 是 | — | 否 | 2 |
| five_only | `"Buzz"` | `"Buzz"` | 是 | — | 否 | 2 |
| both_three_and_five | `"FizzBuzz"` | `"FizzBuzz"` | 是 | — | 否 | 2 |
| neither | `"7"` | `"7"` | 是 | — | 否 | 2 |

## 11. 人工代码审查

人工审查确认：修复仅把逻辑或改为逻辑与，分支顺序合理；入口函数签名与返回类型未变；未引入对异常输入的额外假设。属于最小必要修改，通过代码审查。

## 12. 最终评价

修复有效。原始代码在 three_only、five_only 用例上返回错误值（失败 2/4），修复代码 4/4 通过。该案例验证了分支条件逻辑错误的定位与修复。

