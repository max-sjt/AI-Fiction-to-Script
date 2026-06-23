# AI Fiction to Script

> 将多章节小说快速改编为结构化、可编辑、可版本管理的 YAML 剧本草稿。

`ai-fiction-to-script` 是一个面向小说改编、短剧开发和剧本文案工作流的 AI 辅助工具。它可以读取小说文本或章节目录，生成符合 Schema 的 YAML 剧本，并提供 Web 工作台、CLI、版本管理、差异对比、单场景重生成和 Docker 部署能力。

## 核心特性

- **小说到剧本一键改编**：从多章节小说文本生成 Story Bible、分幕大纲、场景计划和剧本正文。
- **Web + CLI 双入口**：适合本地可视化编辑，也适合批处理、自动化脚本和测试流水线。
- **可追溯版本管理**：每次生成、编辑、重生成都会落盘到 `.novel2script`，支持版本列表、diff 和回看。
- **单场景重生成**：针对指定 `scene_id` 追加改写指令，保留原项目上下文并生成新版本。
- **模型与缓存可配置**：支持 Mock 本地演示、Qwen / DashScope 调用、Redis Web 缓存和 Docker Compose 三层部署。

## 技术栈

- **语言与运行时**：Python 3.12+
- **CLI**：Typer、Rich
- **数据建模**：Pydantic v2
- **YAML / Schema**：PyYAML、项目内置 JSON Schema 导出
- **AI 调用**：httpx、Qwen / DashScope OpenAI-Compatible API
- **Web 服务**：Python `ThreadingHTTPServer`
- **前端**：原生 HTML / CSS / JavaScript
- **缓存与部署**：Redis、Docker、Docker Compose、Nginx

## 快速开始

### 环境要求

| 依赖 | 版本 / 说明 |
| --- | --- |
| Python | `>= 3.12` |
| pip | 建议使用 Python 自带最新版 |
| Git | 用于克隆仓库 |
| Docker | 可选，仅 Docker 部署需要 |
| Redis | 可选，Web 缓存需要；Docker Compose 会自动启动 |
| Qwen / DashScope API Key | 可选；不配置时可使用 `mock` 模式跑通流程 |

### 1. 克隆并安装

```bash
git clone [待补充: 仓库地址]
cd AI-Fiction-to-Script
python -m pip install --upgrade pip
python -m pip install -e .
```

验证安装：

```bash
python -m ai_fiction_to_script.cli version
novel2script --help
```

### 2. 5 分钟本地跑通

三种启动方式：
```
1、 novel2script web --host 127.0.0.1 --port 8098 --version-root .novel2script
浏览器访问http://127.0.0.1:8098

2、测试 CLI 流程：
  novel2script quick examples/sample_novel.txt --provider mock --detail fast 

3、 如果用 Docker 启动整套服务：
docker compose up --build
```

不需要外部模型，直接使用 `mock` 模式生成示例 YAML：

```bash
novel2script quick examples/sample_novel.txt --provider mock --detail fast
```

生成结果默认写入：

```text
output/sample_novel.yaml
.novel2script/sample_novel/versions/v0001/
```

校验 YAML：

```bash
novel2script validate output/sample_novel.yaml
```

### 3. 启动 Web 工作台

```bash
novel2script web --host 127.0.0.1 --port 8098 --version-root .novel2script
```

浏览器访问：

```text
http://127.0.0.1:8098
```

健康检查：

```bash
curl http://127.0.0.1:8098/api/health
```

Windows PowerShell 可使用：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8098/api/health
```

## 使用示例

### CLI：完整改编命令

```bash
novel2script adapt examples/sample_novel.txt \
  --title "老街回声" \
  --original-author "测试作者" \
  --project-id demo-project \
  --target-format tv_drama \
  --genre "悬疑,都市" \
  --tone balanced \
  --provider mock \
  --detail standard \
  --output output/demo-project.yaml \
  --version-root .novel2script \
  --note "first draft"
```

### CLI：使用 Qwen / DashScope

```bash
export DASHSCOPE_API_KEY="[待补充: 你的 DashScope API Key]"

novel2script quick examples/sample_novel.txt \
  --title "老街回声" \
  --provider qwen \
  --model qwen3.6-flash \
  --detail standard
```

Windows PowerShell：

```powershell
$env:DASHSCOPE_API_KEY="[待补充: 你的 DashScope API Key]"

novel2script quick examples/sample_novel.txt `
  --title "老街回声" `
  --provider qwen `
  --model qwen3.6-flash `
  --detail standard
```

### CLI：单场景重生成

```bash
novel2script regenerate-scene demo-project v0001 s001 \
  --instruction "加强主角发现线索后的紧迫感，并减少旁白。" \
  --provider mock \
  --version-root .novel2script \
  --note "rewrite opening scene"
```

### HTTP API：提交异步改编任务

启动 Web 服务后，可以通过 API 创建任务：

```bash
curl -X POST http://127.0.0.1:8098/api/adapt-async \
  -H "Content-Type: application/json" \
  -d '{
    "title": "老街回声",
    "original_author": "测试作者",
    "script_type": "tv_drama",
    "tone": "balanced",
    "genre": "悬疑,都市",
    "provider": "mock",
    "detail_level": "fast",
    "novel_text": "第一章\n雨夜里，老街尽头的照相馆重新亮起灯。\n\n第二章\n主角发现旧照片背后藏着一串地址。\n\n第三章\n地址指向二十年前失踪案的最后现场。"
  }'
```

返回结果中会包含 `task.task_id`。随后轮询任务状态：

```bash
curl http://127.0.0.1:8098/api/tasks/[待补充: task_id]
```

## 常用命令

| 场景 | 命令 |
| --- | --- |
| 查看版本 | `novel2script version` |
| 快速生成 | `novel2script quick examples/sample_novel.txt --provider mock` |
| 完整生成 | `novel2script adapt examples/sample_novel.txt --title "Demo" --project-id demo` |
| 校验 YAML | `novel2script validate output/sample_novel.yaml` |
| 查看版本列表 | `novel2script list-versions demo-project --version-root .novel2script` |
| 对比版本 | `novel2script diff demo-project v0001 v0002 --version-root .novel2script` |
| 重生成场景 | `novel2script regenerate-scene demo-project v0001 s001 --instruction "..."` |
| 导出 JSON Schema | `novel2script export-schema --output schemas/screenplay.schema.json` |
| 启动 Web | `novel2script web --host 127.0.0.1 --port 8098` |

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DASHSCOPE_API_KEY` | 空 | DashScope / Qwen API Key。`provider=qwen` 时需要。 |
| `QWEN_API_KEY` | 空 | `DASHSCOPE_API_KEY` 的备用变量名。 |
| `QWEN_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | Qwen OpenAI-Compatible API 地址。 |
| `QWEN_TIMEOUT_SECONDS` | `150` | Qwen 请求超时时间。 |
| `WEB_CACHE_ENABLED` | `1` | 是否启用 Web 缓存；`0`、`false`、`no` 表示关闭。 |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis 连接地址。 |
| `WEB_CACHE_TTL_SECONDS` | `60` | Web 缓存过期时间，单位秒。 |
| `WEB_CACHE_KEY_PREFIX` | `novel2script` | Redis 缓存 key 前缀。 |

### 关键目录

| 路径 | 说明 |
| --- | --- |
| `src/ai_fiction_to_script/` | Python 源码目录。 |
| `src/ai_fiction_to_script/web/static/` | Web 工作台前端静态资源。 |
| `examples/` | 示例小说文本与生成样例。 |
| `schemas/screenplay.schema.json` | 剧本 YAML 对应的 JSON Schema。 |
| `docs/` | 架构、Schema、基线版本等补充文档。 |
| `output/` | CLI 默认输出目录。 |
| `.novel2script/` | 本地版本库，保存每次生成结果与中间产物。 |
| `runtime/` | 运行期日志目录，例如异步任务错误日志。 |

### 生成细节档位

| `--detail` | 适用场景 | 说明 |
| --- | --- | --- |
| `fast` | 快速预览 | 更少上下文与更短正文，适合验证流程和结构。 |
| `standard` | 标准初稿 | 默认档位，兼顾速度与完整度。 |
| `detailed` | 详写草稿 | 更多上下文与更丰富正文，适合进一步打磨。 |

## Docker 部署

使用 Docker Compose 启动 App、Redis 和 Nginx：

```bash
docker compose up --build
```

访问：

```text
http://127.0.0.1:8080
```

停止：

```bash
docker compose down
```

Compose 部署会将本地 `.novel2script` 挂载到容器内，便于持久化版本数据。

## Windows 本地三层栈

项目提供了 Windows 本地启动脚本：

```powershell
.\scripts\run_local_stack.ps1
```

访问：

```text
http://127.0.0.1:8088
```

停止：

```powershell
.\scripts\stop_local_stack.ps1
```

## 输出格式

生成的 YAML 文档包含以下核心结构：

```yaml
schema_version: "2.0"
meta:
  title: "老街回声"
source:
  chapter_count: 3
story_bible:
  characters: []
outline:
  acts: []
  scene_plans: []
script:
  acts: []
quality:
  confidence: 0.0
extensions: {}
```

如需重新生成 Schema：

```bash
novel2script export-schema --output schemas/screenplay.schema.json
```

更多说明见：

- [docs/SCREENPLAY_YAML_SCHEMA_DESIGN.md](docs/SCREENPLAY_YAML_SCHEMA_DESIGN.md)
- [docs/YAML_SCHEMA.md](docs/YAML_SCHEMA.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 测试

安装测试依赖后运行：

```bash
python -m pip install -e .
python -m pytest -q
```

如果本地没有安装 `pytest`，请先安装：

```bash
python -m pip install pytest
```

## 安全说明

- 不要把真实 API Key 写入 README、示例文件或提交记录。
- 推荐使用环境变量传入 `DASHSCOPE_API_KEY` / `QWEN_API_KEY`。
- `.novel2script/` 会保存生成结果与中间产物，如包含敏感文本，请按团队规范管理访问权限。

## 贡献指南

欢迎通过 Issue 和 Pull Request 改进项目。

1. Fork 本仓库并创建特性分支：

   ```bash
   git checkout -b feat/your-feature
   ```

2. 保持改动聚焦，并为核心逻辑补充测试。
3. 提交前运行测试：

   ```bash
   python -m pytest -q
   ```

4. 提交 PR 时请说明：
   - 变更目的与影响范围
   - 主要实现思路
   - 已执行的测试命令
   - 兼容性或迁移注意事项

代码规范建议：

- Python 代码遵循类型标注优先、函数职责清晰的风格。
- CLI 参数、Web API 字段和 YAML Schema 的变更需要同步更新文档与测试。
- 不提交生成缓存、私钥、真实 API Key、大体积临时文件和个人环境配置。

