# AI 小说转剧本工具

`AI Fiction to Script` 是一个基于 Qwen 的小说改编工具，用来把原始小说文本整理成结构化、可编辑的 YAML 剧本草稿，适合做快速生成、版本迭代和场景级修改。

整个生成流程分为几个阶段：

1. 解析上传文件或粘贴的小说正文
2. 提取章节信息并整理故事资料
3. 生成剧本大纲
4. 生成场景级剧本内容
5. 校验结构完整性与连续性

## 当前版本

- `v0.4.0`
- 已提供命令行工作流、本地版本库、Schema 导出、场景重生成和可视化 Web 工作台

## 核心能力

- 将小说内容转换为结构化 YAML 剧本草稿
- 保留章节引用，方便追溯原文来源
- 为每次生成结果保存本地版本
- 支持版本差异比较
- 支持单场景重生成，无需整项目重跑
- 支持在浏览器工作台中直接查看、下载和调整结果
- Web 模式支持更快的草稿生成路径，优先减少等待时间

## 目录结构

- `src/ai_fiction_to_script/models/`：Pydantic 数据模型与运行时模型
- `src/ai_fiction_to_script/services/`：解析、生成、校验、版本管理与工作台服务
- `src/ai_fiction_to_script/pipeline/`：改编流程编排引擎
- `src/ai_fiction_to_script/web/`：轻量 Web 服务与静态前端资源
- `docs/`：架构与 Schema 文档
- `examples/`：示例输入
- `tests/`：CLI、Pipeline、Web API 与工作台测试

## 安装

```bash
pip install -e .
```

如果之前安装过旧版本的可编辑包，拉取最新代码后建议重新执行一次安装命令，确保 `novel2script web` 等入口与当前源码保持一致。

## Qwen 配置

调用在线 Qwen 之前，请先设置 DashScope / Qwen API Key：

```bash
set DASHSCOPE_API_KEY=your_key_here
```

可选环境变量：

- `QWEN_BASE_URL`
- `QWEN_TIMEOUT_SECONDS`

如果你的账号不在默认地域，需要把 `QWEN_BASE_URL` 设置成对应地域的 DashScope OpenAI 兼容地址。

## CLI 用法

从文本文件生成剧本草稿：

```bash
novel2script adapt examples/sample_novel.txt --title 老街回声 --original-author 测试作者 --project-id demo-project
```

查看已保存版本：

```bash
novel2script list-versions demo-project
```

重生成单个场景：

```bash
novel2script regenerate-scene demo-project v0001 s001 --instruction "强化主角的紧迫感。"
```

导出 JSON Schema：

```bash
novel2script export-schema --output schemas/screenplay.schema.json
```

## Web 工作台

启动可视化工作台：

```bash
novel2script web --host 127.0.0.1 --port 8098
```

然后在浏览器中打开：

```text
http://127.0.0.1:8098
```

工作台支持：

- 通过文件上传或直接粘贴小说文本生成剧本
- 浏览项目与版本
- 查看最终生成剧本
- 下载 YAML 结果
- 按修改要求进行场景重生成
- 查看重生成前后对比
- 在 `中文` 与 `English` 界面之间切换

补充说明：

- 现在支持单章或多章文本输入，但多章输入通常会得到更稳定的结果
- Web 模式默认优先走更快的生成路径，但真实 Qwen 生成速度仍受网络和模型响应影响

## 本地版本管理

工具内部维护两层版本：

- 源代码版本：Git 分支、提交和标签
- 剧本产物版本：`.novel2script/<project>/versions/v000x/`

每个保存版本包含：

- `screenplay.yaml`
- `screenplay.json`
- `intermediates/*.json`
- `index.json`

## 校验与测试

运行测试：

```bash
python -m pytest -q
```

## 文档

- [架构说明](docs/ARCHITECTURE.md)
- [YAML Schema 说明](docs/YAML_SCHEMA.md)
- [变更记录](CHANGELOG.md)
