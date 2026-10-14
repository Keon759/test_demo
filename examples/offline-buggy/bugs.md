# 自动生成的本地缺陷单

交付方式：生成文件；未向 GitHub Issues、Jira 或其他平台提交。

## BUG-803FA60AA1：用户名低于最小长度：实际结果不符合预期

- 状态：open
- 关联需求：REG-002
- 关联用例：TC-REG-005
- PRD 原文：用户名长度必须大于等于 6 位。
- 前置注册：`[]`
- 请求：POST `/api/register`，`{"username": "uuuuu", "password": "ppppppppp"}`
- 预期状态码：400
- 实际状态码：201
- 实际响应：`{"message": "注册成功", "username": "uuuuu"}`
