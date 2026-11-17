# 案例 C03：拼接姓名时未处理 None 空值

## 1. 编号

- 编号：C03　类别：空值处理错误

## 2. 问题描述

函数 full_name(first, last) 应将名字与姓氏拼接，缺失的部分（None）视为空字符串并去掉多余空格。原始代码直接对参数调用 .strip()，当任一参数为 None 时抛出 AttributeError。

## 3. 原始代码

```python
def full_name(first, last):
    return first.strip() + " " + last.strip()
```

## 4. Bug 原因

未对 None 做归一化处理，None 没有 strip 方法导致 AttributeError；即使不是 None，简单拼接也会在某一部分为空时留下多余空格。

## 5. 修复要求

使用 (value or "").strip() 归一化两个参数，拼接后再整体 strip，保证 None 与空字符串都得到合理结果。

## 6. AI 修复过程

- 执行者：本次由 AI 辅助完成定位与修复（CodeBuddy Code 执行分析与改写）

**分析步骤**

1. 识别原始代码对两个参数都直接调用 .strip()，推断 None 输入会触发 AttributeError。
1. 明确需求：缺失部分按空字符串处理，且结果不留首尾空格。
1. 确认非空输入的正常路径需保持原样。

**修复步骤**

1. 引入 (first or "").strip() 与 (last or "").strip() 完成空值归一化。
1. 对拼接结果整体 strip 以消除边界空格。

**复测步骤**

1. 通过真实独立子进程运行三组用例：均非空、last 为 None、first 为 None。
1. 比对返回值，确认空值用例修复前报错、修复后返回预期字符串。
1. 确认修复代码全部通过。

> 未保存模型对话原文，不提供虚构的对话记录。

## 7. 修复后代码

```python
def full_name(first, last):
    first = (first or "").strip()
    last = (last or "").strip()
    return (first + " " + last).strip()
```

## 8. 测试用例

| 用例 | 输入参数(args) | 期望(expected) | 超时(ms) |
| --- | --- | --- | ---: |
| both_present | `["Ada", "Lovelace"]` | `"Ada Lovelace"` | 2000 |
| last_is_none | `["Ada", null]` | `"Ada"` | 2000 |
| first_is_none | `[null, "Lovelace"]` | `"Lovelace"` | 2000 |

## 9. 修复前结果（原始代码真实执行）

- 通过：1/3　全部通过：否

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| both_present | `"Ada Lovelace"` | `"Ada Lovelace"` | 是 | — | 否 | 2 |
| last_is_none | `"Ada"` | `null` | 否 | 'NoneType' object has no attribute 'strip' | 否 | 10 |
| first_is_none | `"Lovelace"` | `null` | 否 | 'NoneType' object has no attribute 'strip' | 否 | 10 |

## 10. 修复后结果（修复代码真实执行）

- 通过：3/3　全部通过：是

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| both_present | `"Ada Lovelace"` | `"Ada Lovelace"` | 是 | — | 否 | 2 |
| last_is_none | `"Ada"` | `"Ada"` | 是 | — | 否 | 2 |
| first_is_none | `"Lovelace"` | `"Lovelace"` | 是 | — | 否 | 2 |

## 11. 人工代码审查

人工审查确认：归一化写法简洁，None 与空字符串等价处理符合语义；整体 strip 消除多余空格；对正常输入无回归影响。

## 12. 最终评价

修复有效。原始代码在两个 None 用例上抛出 AttributeError（失败 2/3），修复代码 3/3 通过。展示了空值防御的必要性。

