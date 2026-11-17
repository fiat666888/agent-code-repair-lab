# 案例 C05：解析配置整数未捕获异常

## 1. 编号

- 编号：C05　类别：异常处理错误

## 2. 问题描述

函数 parse_config_int(text) 应把配置字符串解析为整数；当输入无法解析（非数字、含小数点等）时应返回默认值 0，而不是让异常向外扩散导致调用方崩溃。原始代码直接调用 int(text)。

## 3. 原始代码

```python
def parse_config_int(text):
    return int(text)
```

## 4. Bug 原因

缺少异常处理：int() 在遇到非数字字符串时抛 ValueError，遇到 None 时抛 TypeError，未按要求降级为默认值。

## 5. 修复要求

用 try/except 包裹 int(text)，捕获 (TypeError, ValueError) 并返回 0；合法输入保持原解析结果。

## 6. AI 修复过程

- 执行者：本次由 AI 辅助完成定位与修复（CodeBuddy Code 执行分析与改写）

**分析步骤**

1. 对照需求确认非法输入应返回 0 而非抛出异常。
1. 识别 int() 在 'abc' 上抛 ValueError、在 '3.14' 上同样抛 ValueError。
1. 判断需要用 try/except 建立降级路径。

**修复步骤**

1. 增加 try/except (TypeError, ValueError) 结构。
1. 异常分支返回默认值 0，成功分支返回 int(text)。

**复测步骤**

1. 通过真实独立子进程运行合法数字、非数字、带小数点三组用例。
1. 比对返回值，确认修复前非法输入报错、修复后返回 0。
1. 确认修复代码全部通过。

> 未保存模型对话原文，不提供虚构的对话记录。

## 7. 修复后代码

```python
def parse_config_int(text):
    try:
        return int(text)
    except (TypeError, ValueError):
        return 0
```

## 8. 测试用例

| 用例 | 输入参数(args) | 期望(expected) | 超时(ms) |
| --- | --- | --- | ---: |
| valid_integer | `["42"]` | `42` | 2000 |
| non_numeric | `["abc"]` | `0` | 2000 |
| decimal_string | `["3.14"]` | `0` | 2000 |

## 9. 修复前结果（原始代码真实执行）

- 通过：1/3　全部通过：否

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| valid_integer | `42` | `42` | 是 | — | 否 | 2 |
| non_numeric | `0` | `null` | 否 | invalid literal for int() with base 10: 'abc' | 否 | 10 |
| decimal_string | `0` | `null` | 否 | invalid literal for int() with base 10: '3.14' | 否 | 11 |

## 10. 修复后结果（修复代码真实执行）

- 通过：3/3　全部通过：是

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| valid_integer | `42` | `42` | 是 | — | 否 | 2 |
| non_numeric | `0` | `0` | 是 | — | 否 | 2 |
| decimal_string | `0` | `0` | 是 | — | 否 | 2 |

## 11. 人工代码审查

人工审查确认：捕获的异常类型覆盖 int() 的常见失败情形；返回类型始终为 int，接口稳定；未过度捕获 Exception，避免掩盖无关错误。

## 12. 最终评价

修复有效。原始代码在 non_numeric、decimal_string 上抛 ValueError（失败 2/3），修复代码 3/3 通过。展示了异常降级处理的正确做法。

