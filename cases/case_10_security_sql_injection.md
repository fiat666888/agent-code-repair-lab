# 案例 C10：SQL 注入：字符串拼接查询改为参数化查询并校验输入

## 1. 编号

- 编号：C10　类别：安全问题

## 2. 问题描述

函数 login(username) 在 sqlite3 内存用户表中按用户名查密码。原始代码用字符串拼接构造 SQL，攻击者输入 ' OR '1'='1 可绕过条件读取全部用户密码。需改为参数化查询并加入用户名白名单校验，测试必须能区分修复前后。

## 3. 原始代码

```python
import sqlite3


def login(username):
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE users (username TEXT, password TEXT)')
    conn.executemany('INSERT INTO users VALUES (?, ?)', [('alice', 's3cret-A'), ('bob', 'p4ss-B')])
    sql = "SELECT password FROM users WHERE username = '" + username + "'"
    rows = conn.execute(sql).fetchall()
    conn.close()
    return [r[0] for r in rows]
```

## 4. Bug 原因

使用字符串拼接把不可信输入直接嵌入 SQL 语句，输入中的单引号改变了查询结构，形成 SQL 注入，可读取任意甚至全部用户数据。

## 5. 修复要求

改用参数化查询 SELECT ... WHERE username = ? 并传入 (username,)；同时用正则白名单限制用户名只允许字母、数字、下划线且长度 1-32，非法输入返回空列表。

## 6. AI 修复过程

- 执行者：本次由 AI 辅助完成定位与修复（CodeBuddy Code 执行分析与改写）

**分析步骤**

1. 识别 sql 由字符串拼接构造，用户输入中的引号可改变语句结构。
1. 推演注入输入 ' OR '1'='1 使 WHERE 恒真，返回全部密码；注释型输入 alice' -- 也能绕过。
1. 确定两层防御：输入白名单校验 + 参数化查询。

**修复步骤**

1. 引入 re 模块，用 re.fullmatch(r'[A-Za-z0-9_]{1,32}', username) 做白名单校验并拒绝非字符串。
1. 把查询改为参数化形式 execute('... username = ?', (username,))。
1. 非法输入时关闭连接并返回 []。

**复测步骤**

1. 通过真实独立子进程运行合法登录、OR 注入、注释注入三组用例。
1. 比对实际返回密码列表：注入用例修复前应泄露数据、修复后为 []。
1. 确认合法登录仍返回正确密码且修复代码全部通过。

> 未保存模型对话原文，不提供虚构的对话记录。

## 7. 修复后代码

```python
import re
import sqlite3


def login(username):
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE users (username TEXT, password TEXT)')
    conn.executemany('INSERT INTO users VALUES (?, ?)', [('alice', 's3cret-A'), ('bob', 'p4ss-B')])
    if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z0-9_]{1,32}', username):
        conn.close()
        return []
    rows = conn.execute('SELECT password FROM users WHERE username = ?', (username,)).fetchall()
    conn.close()
    return [r[0] for r in rows]
```

## 8. 测试用例

| 用例 | 输入参数(args) | 期望(expected) | 超时(ms) |
| --- | --- | --- | ---: |
| valid_login | `["alice"]` | `["s3cret-A"]` | 2000 |
| or_injection | `["' OR '1'='1"]` | `[]` | 2000 |
| comment_injection | `["alice' --"]` | `[]` | 2000 |

## 9. 修复前结果（原始代码真实执行）

- 通过：1/3　全部通过：否

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| valid_login | `["s3cret-A"]` | `["s3cret-A"]` | 是 | — | 否 | 14 |
| or_injection | `[]` | `["s3cret-A", "p4ss-B"]` | 否 | — | 否 | 13 |
| comment_injection | `[]` | `["s3cret-A"]` | 否 | — | 否 | 12 |

## 10. 修复后结果（修复代码真实执行）

- 通过：3/3　全部通过：是

| 用例 | 期望 | 实际 | 通过 | 错误 | 超时 | 耗时(ms) |
| --- | --- | --- | :---: | --- | :---: | ---: |
| valid_login | `["s3cret-A"]` | `["s3cret-A"]` | 是 | — | 否 | 12 |
| or_injection | `[]` | `[]` | 是 | — | 否 | 12 |
| comment_injection | `[]` | `[]` | 是 | — | 否 | 12 |

## 11. 人工代码审查

人工审查确认：参数化查询从根本上隔离了数据与 SQL 结构；正则白名单进一步缩小攻击面；合法用户名路径未受影响；连接在两分支均正确关闭。属可运行的真实安全修复。

## 12. 最终评价

修复有效。原始代码在两个注入用例上泄露密码（失败 2/3），修复代码 3/3 通过，注入输入均返回 []。真实展示了 SQL 注入危害与参数化防御。

