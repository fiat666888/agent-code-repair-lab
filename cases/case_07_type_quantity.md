# 案例 C07：外部传入的字符串数量未转换为数字导致乘法类型错误

## 1. 编号

- 编号：C07　类别：类型错误

## 2. 问题描述

函数 calculate_total(price, quantity) 应返回总价。quantity 可能来自表单或配置，以字符串形式传入（如 "3"）。原始代码直接 price * quantity，在 price 为 float、quantity 为 str 时抛出 TypeError。

## 3. 原始代码

```python
def calculate_total(price, quantity):
    return price * quantity
```

## 4. Bug 原因

未对外部输入做类型转换，float 与 str 执行乘法时抛出 TypeError: can't multiply sequence by non-int of type 'float'。

## 5. 修复要求

在计算前显式转换类型：float(price) * int(quantity)，使字符串数量与价格都能正确参与运算。

## 6. AI 修复过程

- 执行者：本次由 AI 辅助完成定位与修复（CodeBuddy Code 执行分析与改写）

**分析步骤**

1. 检查调用场景：quantity 可能为字符串，而 price 为浮点数。
1. 推断 price * quantity 在 float 与 str 组合下必然 TypeError。
1. 确认需要显式转换为数值类型，而非修改运算符号。

**修复步骤**

1. 把返回表达式改为 float(price) * int(quantity)。
1. 保持函数签名与返回数值类型不变。

**复测步骤**

1. 通过真实独立子进程运行 quantity 为字符串与为整数两组用例。
1. 比对实际返回值，确认修复前 TypeError、修复后返回 300.0 与 100.0。
1. 确认修复代码全部通过。

> 未保存模型对话原文，不提供虚构的对话记录。

## 7. 修复后代码

```python
def calculate_total(price, quantity):
    return float(price) * int(quantity)
```

## 8. 测试用例

| 用例 | 输入参数(args) | 期望(expected) | 超时(ms) |
| --- | --- | --- | ---: |
| string_quantity | `[100.0, "3"]` | `300.0` | 2000 |
| int_quantity | `[50.0, 2]` | `100.0` | 2000 |

## 9. 修复前结果（原始代码真实执行）

- 通过：1/2　全部通过：否

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| string_quantity | `300.0` | `null` | 否 | can't multiply sequence by non-int of type 'float' | 否 | 11 |
| int_quantity | `100.0` | `100.0` | 是 | — | 否 | 2 |

## 10. 修复后结果（修复代码真实执行）

- 通过：2/2　全部通过：是

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| string_quantity | `300.0` | `300.0` | 是 | — | 否 | 2 |
| int_quantity | `100.0` | `100.0` | 是 | — | 否 | 2 |

## 11. 人工代码审查

人工审查确认：显式 float/int 转换使类型意图清晰；对原本合法的数值输入无回归；返回仍为浮点数。属于边界明确的输入类型修复。

## 12. 最终评价

修复有效。原始代码在 string_quantity 用例抛出 TypeError（失败 1/2），修复代码 2/2 通过。体现了外部输入类型转换的重要性。

