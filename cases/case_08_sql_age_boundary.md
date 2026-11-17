# 案例 C08：sqlite3 成年用户查询边界条件 > 误用为 >=

## 1. 编号

- 编号：C08　类别：SQL查询问题

## 2. 问题描述

函数 get_adult_names() 使用 Python sqlite3 内存库，查询 age >= 18 的成年用户姓名并按姓名排序。原始 SQL 写成 age > 18，恰好 18 岁的用户被漏掉。需通过真实查询比较修复前后的结果集。

## 3. 原始代码

```python
def get_adult_names():
    import sqlite3
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE users (id INTEGER, name TEXT, age INTEGER)')
    conn.executemany('INSERT INTO users VALUES (?, ?, ?)', [(1, 'Alice', 30), (2, 'Bob', 17), (3, 'Carol', 25), (4, 'Dave', 18)])
    rows = conn.execute('SELECT name FROM users WHERE age > 18 ORDER BY name').fetchall()
    conn.close()
    return [r[0] for r in rows]
```

## 4. Bug 原因

错误 SQL 使用严格大于 age > 18，导致 18 岁的 Dave 被排除；正确语义应为 age >= 18。此为查询条件边界错误，真实改变了结果行。

## 5. 修复要求

把 SQL 中的 age > 18 改为 age >= 18，其余建表、插入、排序与连接管理保持不变，使查询结果包含恰好 18 岁的用户。

## 6. AI 修复过程

- 执行者：本次由 AI 辅助完成定位与修复（CodeBuddy Code 执行分析与改写）

**分析步骤**

1. 读取题目「成年 = age >= 18」与数据中 Dave=18 这一边界样本。
1. 检查原始 SQL 使用 age > 18，推断 Dave 会被过滤掉。
1. 确认 ORDER BY 与连接关闭逻辑正确，无需改动。

**修复步骤**

1. 仅将 SQL 条件由 > 改为 >=。
1. 保持 sqlite3 内存库的建表与参数化插入不变。

**复测步骤**

1. 通过真实独立子进程执行原始与修复代码，sqlite3 在子进程临时目录内正常运行。
1. 比对返回姓名列表：修复前为 ['Alice','Carol']，修复后应含 'Dave'。
1. 确认修复代码全部通过。

> 未保存模型对话原文，不提供虚构的对话记录。

## 7. 修复后代码

```python
def get_adult_names():
    import sqlite3
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE users (id INTEGER, name TEXT, age INTEGER)')
    conn.executemany('INSERT INTO users VALUES (?, ?, ?)', [(1, 'Alice', 30), (2, 'Bob', 17), (3, 'Carol', 25), (4, 'Dave', 18)])
    rows = conn.execute('SELECT name FROM users WHERE age >= 18 ORDER BY name').fetchall()
    conn.close()
    return [r[0] for r in rows]
```

## 8. 测试用例

| 用例 | 输入参数(args) | 期望(expected) | 超时(ms) |
| --- | --- | --- | ---: |
| adult_names_includes_18 | `[]` | `["Alice", "Carol", "Dave"]` | 2000 |

## 9. 修复前结果（原始代码真实执行）

- 通过：0/1　全部通过：否

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| adult_names_includes_18 | `["Alice", "Carol", "Dave"]` | `["Alice", "Carol"]` | 否 | — | 否 | 13 |

## 10. 修复后结果（修复代码真实执行）

- 通过：1/1　全部通过：是

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| adult_names_includes_18 | `["Alice", "Carol", "Dave"]` | `["Alice", "Carol", "Dave"]` | 是 | — | 否 | 13 |

## 11. 人工代码审查

人工审查确认：SQL 条件修改与题目语义一致；仍使用参数化插入避免注入；连接在函数内正确关闭；结果按姓名排序稳定。

## 12. 最终评价

修复有效。原始代码返回 ['Alice','Carol'] 漏掉 Dave（失败 1/1），修复代码返回 ['Alice','Carol','Dave']，1/1 通过。基于真实 sqlite3 查询结果比较得出。

