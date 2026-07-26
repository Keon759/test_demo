# 🤖 AI Automation Testing Demo (PoC Prototype)

> 一个基于 AI 驱动的一站式自动化测试插件全流程最小可验证原型（Proof of Concept）。
> 涵盖 **PRD 分析 ➔ 需求结构化拆解 ➔ 测试用例自动生成 ➔ 自动化执行 ➔ 结构化测试报告 ➔ 缺陷（Bug）自动追踪** 的完整闭环。

---

## 📌 Project Overview--项目背景与目的

在无内部大型业务系统权限的情况下，本项目搭建了一个基于 **React + Flask** 的轻量级登录注册 Web 应用作为**自动化测试沙盒（PoC System）**。
通过在系统中**刻意预埋业务规则类缺陷（Bug Injection）**（如用户名长度限制缺失），验证 AI 自动化测试插件从需求解析到缺陷自动提交的端到端可行性。

---

## 🛠️ What's Included

* **`backend/`**：基于 Flask + SQLite 实现的后端 API（提供用户注册、登录校验及测试数据存储功能）。
* **`frontend/`**：基于 React + Ant Design + Axios 构建的前端 UI 界面（响应式控制台看板与交互界面）。
* **`docs/`**：AI 测试插件沉淀的全套结构化工程资产与架构方案：
  * **PRD & Requirements**：产品需求文档与结构化拆解结果。
  * **Test Cases**：AI 提示词（Prompt）导出的结构化 JSON/Markdown 测试用例库。
  * **Execution Log & Report**：测试执行日志与可视化结构化测试报告。
  * **Bug Ticket**：基于发现的预埋 Bug 自动解析并生成的标准缺陷单。
  * **Architecture Notes**：AI 测试插件架构设计与 Prompt 工程规范说明。

---

## 🚀 Quick Start--快速启动指南

### 选项一：使用一键脚本运行（推荐）

直接在根目录下运行对应系统的脚本即可自动完成依赖安装与启动：
* **Windows (PowerShell)**: `.\run-demo.ps1`
* **Windows (CMD/BAT)**: `.\run-demo.bat`

---

### 选项二：手动分步启动

#### 1. 后端服务 (Backend)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py

2.前端服务（Frontend)
cd frontend
npm install
npm run dev
