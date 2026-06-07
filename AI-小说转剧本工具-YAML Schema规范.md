# AI-小说转剧本工具 YAML Schema 规范

## 1. 文档目标

本文档定义 `AI-小说转剧本工具` 的标准输出格式：将 **3 个章节及以上** 的小说文本自动转换为 **结构化剧本 YAML**。

本规范服务于三个直接目标：

1. 让模型输出的剧本可以被程序稳定解析。
2. 让编辑人员可以在 YAML 上直接做人工修改和版本管理。
3. 让每一场戏都能追溯到原小说章节，方便复核、重生成和质量控制。

本文档同时说明 Schema 的设计原因，而不是只给字段清单。

## 2. 适用范围

本 Schema 适用于以下场景：

- 输入为同一部小说的连续文本，且章节数 `>= 3`
- 输出目标为可编辑的剧本初稿，而不是拍摄定稿
- 输出格式为 YAML
- 需要支持后续的局部修订、场景重写、质量校验和版本保存

不适用的场景：

- 单章文本摘要
- 最终拍摄用分镜脚本
- 自动生成视频镜头表

## 3. 设计原则

### 3.1 分层，而不是把所有信息压平

小说转剧本不是“一次吐出全文”这么简单，而是至少包含四层结果：

1. `source`：原始输入被切成哪些章节
2. `story_bible`：全局故事知识库
3. `outline`：改编后的结构规划
4. `script`：真正的剧本正文

这样设计的原因：

- 便于复用中间结果
- 便于只重跑某一层，而不是整条链路重来
- 便于在结构审阅通过后再进入正文生成

### 3.2 所有关键对象都必须有稳定 ID

人物、地点、章节、场景、节拍都必须使用 ID，而不是只靠中文名称。

这样设计的原因：

- 名称可能修改
- 名称可能重复
- 局部重生成、差异对比、引用校验都依赖稳定 ID

### 3.3 每场戏都要可追溯到原文

`chapter_refs` 和 `source_refs` 不是可选装饰，而是核心字段。

这样设计的原因：

- 编辑人员需要确认改编是否忠于原文
- 局部重生成时必须知道这场戏来自哪些章节
- 质量检查时需要定位问题来源

### 3.4 Schema 要优先服务“初稿生产”

本工具的目标不是直接输出最终拍摄文本，而是输出：

- 可读
- 可编辑
- 可校验
- 可重生成

所以本 Schema 会保留 `quality`、`extensions`、`style_guide` 等工程字段。

### 3.5 YAML 优于 JSON

选择 YAML 而不是 JSON 的原因：

- 更适合人工阅读
- 更适合多行文本
- 更适合版本 diff
- 更适合在同一个文件中做人工修订

## 4. 顶层结构

标准剧本 YAML 由以下顶层字段组成：

```yaml
schema_version: "2.0"
meta: {}
source: {}
adaptation: {}
story_bible: {}
outline: {}
script: {}
quality: {}
extensions: {}
```

## 5. 顶层字段定义

### 5.1 `schema_version`

类型：`string`

作用：标识当前 YAML 规范版本。

设计原因：

- 未来字段一定会演进
- 版本号是兼容处理的入口
- 可以支持旧数据迁移

建议值：

```yaml
schema_version: "2.0"
```

### 5.2 `meta`

类型：`object`

作用：记录本次剧本生成的基础项目信息。

推荐字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `project_id` | string | 是 | 项目标识 |
| `title` | string | 是 | 剧本标题 |
| `original_novel_title` | string | 是 | 原小说标题 |
| `original_author` | string | 是 | 原作者 |
| `target_format` | string | 是 | 剧本类型，如 `film`、`tv_drama` |
| `language` | string | 是 | 语言，默认 `zh-CN` |
| `genre` | list[string] | 否 | 题材标签 |
| `tone` | string | 否 | 语气风格 |
| `created_at` | string | 是 | ISO 8601 时间 |
| `model_provider` | string | 否 | 模型提供方 |
| `model_name` | string | 否 | 模型名称 |

设计原因：

- 方便版本管理
- 方便区分输出目标
- 方便记录生成上下文

### 5.3 `source`

类型：`object`

作用：记录原始输入与章节拆分结果。

推荐字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `chapter_count` | integer | 是 | 章节总数，业务要求必须 `>= 3` |
| `chapters` | list[object] | 是 | 章节列表 |

每个 `chapters[]` 元素建议包含：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `chapter_id` | string | 是 | 章节 ID |
| `title` | string | 是 | 章节标题 |
| `raw_text_ref` | string | 是 | 原文引用路径或定位符 |
| `summary` | string | 否 | 章节摘要 |
| `excerpt_count` | integer | 否 | 章节切片数量 |

设计原因：

- 这是“3 章以上输入”的直接校验入口
- 章节是局部重生成的最小上游单位
- 后续场景必须建立在章节引用之上

### 5.4 `adaptation`

类型：`object`

作用：描述这次改编的策略，而不是只描述结果。

推荐字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `adaptation_goal` | string | 是 | 改编目标 |
| `compression_strategy` | string | 否 | 压缩策略 |
| `pacing_policy` | string | 否 | 节奏策略 |
| `structure_type` | string | 否 | 结构类型，如 `three_act` |
| `style_guide` | object | 否 | 风格要求 |

`style_guide` 推荐包含：

- `dialogue_style`
- `narration_style`
- `pacing_style`

设计原因：

- 同一部小说可以有多种改编版本
- 改编策略必须显式记录，才能复现和比较
- 后续场景重写时需要继承这层约束

### 5.5 `story_bible`

类型：`object`

作用：承载跨章节、跨场景的统一故事知识。

推荐字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `logline` | string | 是 | 一句话故事概述 |
| `synopsis` | string | 是 | 故事总梗概 |
| `theme` | list[string] | 否 | 主题列表 |
| `characters` | list[object] | 是 | 人物卡 |
| `locations` | list[object] | 否 | 地点卡 |
| `timeline` | list[object] | 否 | 时间线事件 |
| `props` | list[string] | 否 | 关键道具 |

设计原因：

- 人物一致性不能靠模型临场记忆
- 地点和时间线是跨场景 continuity 的基础
- `story_bible` 是生成正文前最关键的全局约束

### 5.6 `outline`

类型：`object`

作用：定义剧本结构规划。

推荐字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `structure_type` | string | 是 | 结构类型 |
| `acts` | list[object] | 是 | 幕结构 |
| `scene_plans` | list[object] | 是 | 场景规划 |

每个 `scene_plans[]` 至少应包含：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `scene_id` | string | 是 | 场景 ID |
| `act_id` | string | 是 | 所属幕 ID |
| `title` | string | 是 | 场景标题 |
| `objective` | string | 是 | 该场戏的戏剧目标 |
| `chapter_refs` | list[string] | 是 | 章节引用 |
| `conflict` | string | 否 | 场景冲突 |
| `notes` | string | 否 | 生成备注 |

设计原因：

- 正文生成前必须先有结构骨架
- 编辑人员通常先改结构，再改文本
- 局部重生成应以 `scene_plan` 为输入，而不是裸文本

### 5.7 `script`

类型：`object`

作用：承载真正的剧本正文。

推荐层级：

1. `acts`
2. `scenes`
3. `beats`

每个 `scene` 推荐字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `scene_id` | string | 是 | 场景 ID |
| `title` | string | 是 | 场景标题 |
| `chapter_refs` | list[string] | 是 | 来自哪些章节 |
| `location_ref` | string | 否 | 地点引用 |
| `time_of_day` | string | 否 | 时间段 |
| `objective` | string | 是 | 戏剧目标 |
| `summary` | string | 否 | 场景摘要 |
| `beats` | list[object] | 是 | 场景节拍 |
| `transitions` | object | 否 | 转场信息 |
| `source_refs` | list[object] | 是 | 原文追溯引用 |

每个 `beat` 推荐字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `beat_id` | string | 是 | 节拍 ID |
| `type` | enum | 是 | `action` / `dialogue` / `narration` / `transition` |
| `text` | string | 是 | 节拍文本 |
| `speaker_ref` | string | 否 | 对白说话人 |
| `emotion` | string | 否 | 情绪标签 |

设计原因：

- 场景级结构方便重写某一场戏
- `beat` 级结构方便细调节奏
- 对白与动作拆分后，便于后续导出其他格式

### 5.8 `quality`

类型：`object`

作用：记录当前草稿的质量结论。

推荐字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `confidence` | float | 否 | 模型置信度 |
| `warnings` | list[string] | 否 | 风险提示 |
| `revision_suggestions` | list[string] | 否 | 修订建议 |
| `continuity_checks` | object | 否 | 连续性检查结果 |

设计原因：

- AI 初稿天然存在不确定性
- 问题必须显式暴露，而不是藏在文本里
- 便于人工优先处理高风险位置

### 5.9 `extensions`

类型：`object`

作用：预留给业务扩展，不影响核心结构。

适合放：

- 上传来源信息
- 切章策略
- 目标集数建议
- 生产状态标签

设计原因：

- 核心 Schema 要稳定
- 业务字段会持续变化
- 用 `extensions` 隔离非核心信息最稳妥

## 6. 关键约束

本工具的业务约束建议明确写入实现和测试：

1. `source.chapter_count >= 3`
2. `len(source.chapters) == source.chapter_count`
3. 所有 `chapter_id` 唯一
4. 所有 `scene_id` 唯一
5. `outline.scene_plans[].chapter_refs` 不能为空
6. `script.acts[].act_id` 必须能在 `outline.acts` 中找到
7. `scene.chapter_refs` 必须是 `source.chapters[].chapter_id` 的子集
8. `source_refs` 至少能指向一个上游章节
9. `speaker_ref` 必须能在 `story_bible.characters` 中找到
10. `location_ref` 必须能在 `story_bible.locations` 中找到

## 7. 设计原因总结

这套 Schema 的核心，不是“把剧本写成 YAML”这么简单，而是解决下面几个工程问题：

### 7.1 为什么一定要求 3 章以上

- 单章文本不足以稳定抽取人物关系和故事走向
- 3 章以上更适合建立 `story_bible`
- 多章节输入才能真正体现自动改编的结构规划价值

### 7.2 为什么 `story_bible` 和 `script` 分开

- `story_bible` 是全局知识
- `script` 是局部文本
- 分开后，修改人物设定不必直接改正文

### 7.3 为什么 `outline` 独立存在

- 先规划结构，再生成正文，效果更稳定
- 结构问题和文本问题是两类问题，必须分开处理

### 7.4 为什么保留 `quality`

- 工具输出的是“可编辑初稿”
- 既然不是定稿，就要把风险和建议一起交付

### 7.5 为什么保留 `extensions`

- 以后会出现新的业务字段
- 不应该每次都破坏核心 Schema

## 8. 交付建议

建议该工具至少交付两份产物：

1. 一份 Markdown 文档：解释 YAML Schema 设计与约束
2. 一份实际 YAML 样例：证明 Schema 足以承载真实三章小说改编结果

当前仓库内建议对应为：

- 规范文档：`AI-小说转剧本工具-YAML Schema规范.md`
- 样例 YAML：`output/laojiehuisheng_screenplay_v2.yaml`

## 9. 样例说明

本规范配套的 YAML 样例基于已上传小说《老街回声》的三章文本生成，重点体现：

- 章节数满足 `>= 3`
- 每场戏可追溯到原章节
- 人物、地点、道具、时间线被抽取到 `story_bible`
- `outline` 与 `script` 独立存在
- `quality` 和 `extensions` 可以承载工程信息
