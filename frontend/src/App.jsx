import { useState } from "react";
import { Alert, Button, Card, ConfigProvider, Form, Input, Segmented, Space, Statistic, Table, Tag, Typography } from "antd";
import { Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { api } from "./api";

const { Title, Paragraph, Text } = Typography;
const statusLabels = { passed: ["通过", "success"], failed: ["失败", "error"], error: ["执行错误", "warning"] };

function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function Overview({ result, setResult }) {
  const [injectBug, setInjectBug] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  async function run() {
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/api/demo/run", { inject_bug: injectBug });
      setResult(data);
      navigate("/results");
    } catch (exc) {
      setError(exc.response?.data?.message || "执行失败，请确认后端已启动，再重试。");
    } finally {
      setBusy(false);
    }
  }
  return <>
    <section className="hero">
      <div><Tag color="blue">开发 · 测试 · 插件原型</Tag>
        <Title>让一条业务缺陷<br />走完整个测试流程</Title>
        <Paragraph className="lead">从登录注册需求出发，生成用例、执行接口测试、汇总报告，最后生成可追溯的缺陷单。</Paragraph>
        <Space wrap><Link to="/sandbox"><Button size="large">体验登录注册</Button></Link>
          <a href="https://github.com/Keon759/test_demo" target="_blank" rel="noreferrer"><Button size="large" type="text">查看源码 ↗</Button></a></Space>
      </div>
      <Card className="run-card" title="复现测试闭环">
        <Paragraph>同一套用例，分别验证包含缺陷和修复后的系统。</Paragraph>
        <Segmented block value={injectBug ? "buggy" : "fixed"} disabled={busy} onChange={(value) => setInjectBug(value === "buggy")}
          options={[{ label: "保留缺陷", value: "buggy" }, { label: "修复缺陷", value: "fixed" }]} />
        <Paragraph className="mode-description">{injectBug ? "用户名长度不足 6 位仍可注册，用例应发现这条规则缺陷。" : "后端启用用户名长度校验，用同一套用例检查修复结果。"}</Paragraph>
        <Button type="primary" size="large" block loading={busy} onClick={run}>运行完整流程</Button>
        <Text type="secondary" className="run-note">离线规则模式 · 无需密钥 · 每条用例使用独立数据</Text>
        {error && <Alert type="error" message={error} showIcon className="spaced" />}
        {result && <Link to="/results" className="last-result">查看上一次结果 →</Link>}
      </Card>
    </section>
    <div className="flow-grid">{[
      ["01", "需求拆解", "10 条规则保留 PRD 原文引用"],
      ["02", "用例生成", "13 条正向、异常与边界用例"],
      ["03", "隔离执行", "调用真实接口逻辑，逐条比较状态码"],
      ["04", "报告与缺陷", "从执行结果自动汇总，关联需求和用例"],
    ].map(([number, title, description]) => <Card key={number}><Text className="step-number">{number}</Text><Title level={4}>{title}</Title><Text type="secondary">{description}</Text></Card>)}</div>
    <Alert className="spaced" type="info" showIcon message="当前展示范围"
      description="网页演示使用针对本项目 PRD 的离线规则解析，不调用大模型。仓库另提供可选 OpenAI 接口；真实模型效果尚未验证。当前缺陷单保存为文件，尚未推送到外部平台。" />
  </>;
}

function Sandbox() {
  const [mode, setMode] = useState("register");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  async function submit(values) {
    setBusy(true);
    setNotice(null);
    try {
      const { data } = await api.post(`/api/${mode}`, values);
      if (mode === "login") navigate("/sandbox/success", { state: { username: data.user.username } });
      else setNotice({ type: "success", text: data.message + "，现在可以切换到登录。" });
    } catch (exc) {
      setNotice({ type: "error", text: exc.response?.data?.message || "连接失败，请确认后端已启动。" });
    } finally { setBusy(false); }
  }
  return <div className="sandbox-layout">
    <section><Tag color="blue">测试对象</Tag><Title level={2}>登录注册沙盒</Title>
      <Paragraph>体验前后端交互，或输入短用户名观察预埋缺陷。</Paragraph>
      <Alert type="warning" showIcon message="这是测试沙盒，请使用虚构账号"
        description="默认保留用户名最小长度校验缺陷。运行测试流程使用另外的独立数据库，不会改变此处注册的账号。登录成功只验证账号密码，不建立生产级登录会话。" />
    </section>
    <Card title={mode === "register" ? "创建测试账号" : "登录测试账号"}>
      <Segmented block value={mode} disabled={busy} onChange={(value) => { setMode(value); setNotice(null); form.resetFields(); }}
        options={[{ label: "注册", value: "register" }, { label: "登录", value: "login" }]} />
      <Form form={form} layout="vertical" onFinish={submit} className="spaced">
        <Form.Item name="username" label="用户名" rules={[{ required: true, whitespace: true, message: "请输入用户名" }, { max: 128, message: "最多 128 位" }]}>
          <Input autoComplete="username" placeholder="例如 tester01" />
        </Form.Item>
        <Form.Item name="password" label="密码" rules={[{ required: true, message: "请输入密码" }, ...(mode === "register" ? [{ min: 6, message: "密码至少 6 位" }] : []), { max: 128, message: "最多 128 位" }]}>
          <Input.Password autoComplete={mode === "register" ? "new-password" : "current-password"} />
        </Form.Item>
        <Button type="primary" htmlType="submit" block loading={busy}>{mode === "register" ? "注册" : "登录"}</Button>
      </Form>
      {notice && <Alert type={notice.type} message={notice.text} showIcon />}
    </Card>
  </div>;
}

function Results({ result }) {
  if (!result) return <Card><Title level={3}>还没有执行结果</Title><Paragraph>先运行一次测试流程，结果会显示在这里。</Paragraph><Link to="/"><Button type="primary">开始测试</Button></Link></Card>;
  const { summary, metadata, records, bugs } = result;
  const columns = [
    { title: "用例", dataIndex: "case_id", width: 145 },
    { title: "测试场景", dataIndex: "title" },
    { title: "需求", dataIndex: "requirement_ids", render: (ids) => ids.join(", ") },
    { title: "预期 / 实际", key: "codes", render: (_, item) => `${item.expected_status} / ${item.actual_status ?? "未执行"}` },
    { title: "结果", dataIndex: "status", render: (status) => <Tag color={statusLabels[status][1]}>{statusLabels[status][0]}</Tag> },
  ];
  const assets = { "requirements.json": result.requirements, "test-cases.json": result.cases, "execution.json": records, "bugs.json": bugs,
    "plan.json": { requirements: result.requirements, cases: result.cases }, "run.json": { metadata, summary } };
  return <>
    <div className="result-heading"><div><Tag color="blue">离线规则模式 · 本次真实执行</Tag><Title level={2}>测试执行结果</Title>
      <Text type="secondary">{new Date(metadata.generated_at).toLocaleString()} · {metadata.inject_bug ? "保留预埋缺陷" : "已启用修复"}</Text></div>
      <Link to="/"><Button>切换模式再运行</Button></Link></div>
    <div className="stat-grid">{[["用例", summary.total], ["通过", summary.passed], ["失败", summary.failed], ["执行错误", summary.errors], ["缺陷单", summary.bugs]]
      .map(([title, value]) => <Card key={title}><Statistic title={title} value={value} /></Card>)}</div>
    <Alert showIcon className="spaced" type={summary.errors ? "error" : summary.failed ? "warning" : "success"}
      message={summary.errors ? "存在执行错误，请查看记录" : summary.failed ? "已发现业务规则缺陷" : "本次全部用例通过"}
      description={summary.failed ? "失败用例是对预期与实际结果的比较；下面的缺陷单保留需求引用、测试数据和响应。" : "结果只代表这套接口用例的覆盖范围。"} />
    <Card title="逐条执行记录" className="spaced"><Table rowKey="case_id" columns={columns} dataSource={records} pagination={false} scroll={{ x: 780 }} /></Card>
    <Card title="生成的缺陷单" className="spaced">{bugs.length ? bugs.map((bug) => <div key={bug.id} className="bug-ticket">
      <Space wrap><Tag color="red">{bug.id}</Tag><Text strong>{bug.title}</Text></Space>
      <Paragraph>关联需求 {bug.requirement_ids.join(", ")} · 用例 {bug.case_ids.join(", ")}</Paragraph>
      <Paragraph type="secondary">PRD：{bug.source_quotes.join("；")}</Paragraph>
      <pre>{JSON.stringify({ endpoint: bug.endpoint, payload: bug.payload, expected_status: bug.expected_status, actual_status: bug.actual_status, actual_body: bug.actual_body }, null, 2)}</pre>
    </div>) : <Text type="secondary">没有失败用例，本次未生成缺陷单。</Text>}</Card>
    <Card title="下载本次交付物" className="spaced"><Space wrap>
      {Object.entries(assets).map(([name, content]) => <Button key={name} onClick={() => download(name, JSON.stringify(content, null, 2), "application/json;charset=utf-8")}>{name}</Button>)}
      {Object.entries(result.documents).map(([name, content]) => <Button key={name} onClick={() => download(name, content, "text/markdown;charset=utf-8")}>{name}</Button>)}
    </Space><Paragraph className="run-note">文件由本次执行自动生成；缺陷单尚未提交到外部平台。</Paragraph></Card>
  </>;
}

export default function App() {
  const [result, setResult] = useState(null);
  return <ConfigProvider theme={{ token: { colorPrimary: "#2458d6", borderRadius: 12, fontFamily: '"Segoe UI", "Microsoft YaHei", sans-serif' } }}>
    <div className="app-shell"><header><Link className="brand" to="/">QA / Prototype</Link><nav>
      <NavLink to="/" end>项目概览</NavLink><NavLink to="/sandbox">登录注册</NavLink><NavLink to="/results">执行结果</NavLink>
    </nav></header><main><Routes>
      <Route path="/" element={<Overview result={result} setResult={setResult} />} />
      <Route path="/sandbox" element={<Sandbox />} />
      <Route path="/sandbox/success" element={<Card><Alert type="success" showIcon message="登录成功" description="已验证账号密码。本沙盒不建立登录会话。" /><Link to="/sandbox"><Button className="spaced">返回沙盒</Button></Link></Card>} />
      <Route path="/results" element={<Results result={result} />} />
      <Route path="*" element={<Card><Title level={3}>页面不存在</Title><Link to="/">返回项目概览</Link></Card>} />
    </Routes></main><footer>React + Ant Design + Flask + SQLite · 可复现的接口测试原型</footer></div>
  </ConfigProvider>;
}
