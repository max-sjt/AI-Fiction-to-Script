# AI-小说转剧本工具 YAML Schema 规范

## 1. 文档目标

本文档定义 `AI-小说转剧本工具` 的标准 YAML 输出结构。该结构以 `老街回声_v0002.yaml` 为整理基准，面向“小说输入 -> 剧本初稿 -> 结构化 YAML -> 局部重生成”的完整工作流。

这份规范的目标是：

1. 让 AI 生成结果可以被程序稳定解析。
2. 让编辑人员可以直接阅读、修改和版本管理 YAML。
3. 让每个场景都能追溯到原小说章节，便于复核、重写和质量检查。
4. 让完整剧本和场景重生成都使用同一套数据结构。

## 2. 适用范围

适用场景：

- 输入为同一部小说的连续章节文本，建议章节数 `>= 3`。
- 输出目标为可编辑剧本初稿，不是最终拍摄分镜。
- 需要保存生成元信息、原文来源、改编策略、故事知识库、场景规划、剧本正文、质量检查和扩展信息。
- 需要支持上传 YAML 后重新生成整篇剧本，或针对单个场景做局部重生成。

不适用场景：

- 单章摘要。
- 最终拍摄用镜头表。
- 纯文本剧本，不需要结构化处理的场景。

## 3. 设计原则

### 3.1 分层保存

YAML 不把全部内容压成一段正文，而是拆成多个层级：

1. `meta`：项目和模型生成信息。
2. `source`：原文输入和章节拆分信息。
3. `adaptation`：改编策略。
4. `story_bible`：人物、地点、时间线、道具等全局设定。
5. `outline`：剧本结构和场景规划。
6. `script`：真正的剧本正文。
7. `quality`：质量检查和修订建议。
8. `extensions`：业务扩展信息。

这样做可以把“故事设定”“场景规划”“剧本文本”“工程信息”分开处理，避免局部重生成时破坏整份文档。

### 3.2 所有关键对象使用稳定 ID

章节、人物、地点、事件、幕、场景、节拍都应使用稳定 ID：

- 章节：`ch01`
- 人物：`c001`
- 地点：`l001`
- 事件：`e001`
- 幕：`main`
- 场景：`s001`
- 节拍：`b001`

名称可以被编辑，但 ID 应尽量保持稳定。版本对比、局部重写、引用校验都依赖这些 ID。

### 3.3 场景必须可追溯

每个场景至少需要通过 `chapter_refs` 指回原章节，并通过 `source_refs` 记录更细的来源定位。

这样做的原因：

- 编辑可以检查改编是否偏离原文。
- 场景重生成时可以精准找到上游素材。
- 质量检查可以定位问题来自哪一章。

### 3.4 YAML 面向初稿生产

该 Schema 的目标不是一次性产出最终定稿，而是产出可继续加工的剧本初稿。因此会保留：

- `quality.warnings`
- `quality.revision_suggestions`
- `extensions.production_notes`
- `extensions.regeneration_bundle`

这些字段用于提示人工复核、后续生产和重生成。

## 4. 顶层结构

标准 YAML 顶层结构如下：

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

说明：Schema 版本号。当前样例使用：

```yaml
schema_version: "2.0"
```

约束：

- 必填。
- 用于未来兼容旧版 YAML。

### 5.2 `meta`

类型：`object`

说明：记录本次生成的项目、格式、语言、模型等元信息。

字段：

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `project_id` | string | 是 | `老街回声` | 项目标识，可用于版本目录或项目列表 |
| `title` | string | 是 | `老街回声` | 剧本标题 |
| `original_novel_title` | string | 是 | `老街回声` | 原小说标题 |
| `original_author` | string | 否 | `sun` | 原作者 |
| `target_format` | string | 是 | `stage_play` | 目标剧本类型 |
| `language` | string | 是 | `zh-CN` | 输出语言 |
| `genre` | list[string] | 否 | `[悬疑]` | 题材标签 |
| `tone` | string | 否 | `angry` | 语气风格 |
| `created_at` | string | 否 | `2026-06-07T08:58:59.436562+00:00` | ISO 8601 时间 |
| `model_provider` | string | 否 | `qwen` | 模型提供方 |
| `model_name` | string | 否 | `qwen3.6-flash` | 模型名称 |

`target_format` 推荐值：

- `film`
- `tv_drama`
- `short_drama`
- `stage_play`
- `animation`
- `audio_drama`

### 5.3 `source`

类型：`object`

说明：记录原始小说输入、章节拆分和原文引用。

字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `chapter_count` | integer | 是 | 章节总数 |
| `chapters` | list[object] | 是 | 章节列表 |

`source.chapters[]` 字段：

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `chapter_id` | string | 是 | `ch01` | 章节 ID |
| `title` | string | 是 | `第一章 雨夜来信` | 章节标题 |
| `raw_text_ref` | string | 否 | `.novel2script\_uploads\老街回声_20260607085859.txt` | 原始上传文本路径或定位符 |
| `summary` | string | 否 | `林然在老街咖啡馆守到打烊...` | 章节摘要 |
| `excerpt_count` | integer | 否 | `1` | 章节切片数量 |

约束：

- `chapter_count` 应等于 `chapters` 的长度。
- 所有 `chapter_id` 必须唯一。
- 业务上建议 `chapter_count >= 3`，以便稳定抽取人物、地点和时间线。

### 5.4 `adaptation`

类型：`object`

说明：记录本次改编策略，描述“要改成什么样”，而不是只保存最终结果。

字段：

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `adaptation_goal` | string | 是 | `将小说改编为舞台剧剧本...` | 改编目标 |
| `compression_strategy` | string | 否 | `merge_minor_events` | 情节压缩策略 |
| `pacing_policy` | string | 否 | `preserve_key_conflicts` | 节奏策略 |
| `structure_type` | string | 否 | `continuous_sequence` | 结构类型 |
| `style_guide` | object | 否 | `{}` | 风格指南 |

`adaptation.style_guide` 字段：

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `dialogue_style` | string | 否 | `锋利压迫` | 对白风格 |
| `narration_style` | string | 否 | `情绪强烈` | 旁白风格 |
| `pacing_style` | string | 否 | `急促` | 节奏风格 |

### 5.5 `story_bible`

类型：`object`

说明：全局故事知识库，供场景规划和剧本正文共享。

字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `logline` | string | 是 | 一句话故事概述 |
| `synopsis` | string | 是 | 故事总梗概 |
| `theme` | list[string] | 否 | 主题列表 |
| `characters` | list[object] | 是 | 人物卡 |
| `locations` | list[object] | 否 | 地点卡 |
| `timeline` | list[object] | 否 | 时间线事件 |
| `props` | list[string] | 否 | 关键道具 |

#### 5.5.1 `story_bible.characters[]`

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `character_id` | string | 是 | `c001` | 人物 ID |
| `name` | string | 是 | `林然` | 人物名 |
| `role` | string | 是 | `protagonist` | 剧作功能 |
| `traits` | list[string] | 否 | `[克制, 有目标]` | 性格特征 |
| `goal` | string | 否 | `推动主线发展` | 角色目标 |
| `conflict` | string | 否 | `在追求目标时遭遇阻力` | 角色冲突 |
| `arc` | string | 否 | `从被动进入主动` | 人物弧光 |
| `voice` | string | 否 | `简洁直接` | 语言风格 |
| `relations` | list[object] | 否 | `[]` | 人物关系 |

`relations[]` 字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `target_character_id` | string | 是 | 指向另一个人物 ID |
| `relation` | string | 是 | 关系说明 |
| `notes` | string | 否 | 补充说明 |

#### 5.5.2 `story_bible.locations[]`

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `location_id` | string | 是 | `l001` | 地点 ID |
| `name` | string | 是 | `老街咖啡馆` | 地点名称 |
| `description` | string | 否 | `与关键事件相关的地点` | 地点描述 |
| `mood` | string | 否 | `悬而未决` | 氛围 |

#### 5.5.3 `story_bible.timeline[]`

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `event_id` | string | 是 | `e001` | 事件 ID |
| `time_order` | integer | 是 | `1` | 时间顺序 |
| `summary` | string | 是 | `林然在老街咖啡馆守到打烊...` | 事件摘要 |
| `chapter_refs` | list[string] | 是 | `[ch01]` | 事件来源章节 |

### 5.6 `outline`

类型：`object`

说明：结构规划层，用于在生成正文前明确幕结构、场景目标和场景之间的衔接。

字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `structure_type` | string | 是 | 结构类型，例如 `continuous_sequence` |
| `acts` | list[object] | 是 | 幕结构 |
| `scene_plans` | list[object] | 是 | 场景规划 |

`outline.acts[]` 字段：

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `act_id` | string | 是 | `main` | 幕 ID |
| `name` | string | 是 | `正文` | 幕名称 |
| `purpose` | string | 是 | `按小说内容连续推进剧情...` | 幕功能 |
| `scene_count` | integer | 否 | `3` | 场景数量 |

`outline.scene_plans[]` 字段：

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `scene_id` | string | 是 | `s001` | 场景 ID |
| `act_id` | string | 是 | `main` | 所属幕 ID |
| `title` | string | 是 | `雨夜来信` | 场景标题 |
| `objective` | string | 是 | `姐姐林薇失踪已经七天...` | 戏剧目标 |
| `chapter_refs` | list[string] | 是 | `[ch01]` | 来源章节 |
| `conflict` | string | 否 | `林然收到匿名短信...` | 场景冲突 |
| `notes` | string | 否 | `林然循着匿名短信...` | 生成备注 |
| `focus_event` | string | 否 | `林然在老街咖啡馆守到打烊...` | 本场聚焦事件 |
| `bridge_in` | string | 否 | `上一场结尾...` | 入场衔接 |
| `bridge_out` | string | 否 | `下一场开端...` | 出场衔接 |

设计说明：

- `outline` 用于控制结构，不直接承载完整剧本文本。
- `scene_plans` 是场景重生成时的重要上下文。
- `bridge_in` 和 `bridge_out` 用于保持场景之间的连续性。

### 5.7 `script`

类型：`object`

说明：承载真正的剧本正文。

层级：

```yaml
script:
  acts:
    - act_id: main
      title: 正文
      scenes: []
```

`script.acts[]` 字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `act_id` | string | 是 | 幕 ID，应能对应 `outline.acts[].act_id` |
| `title` | string | 是 | 幕标题 |
| `scenes` | list[object] | 是 | 场景列表 |

`script.acts[].scenes[]` 字段：

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `scene_id` | string | 是 | `s001` | 场景 ID，应能对应 `outline.scene_plans[].scene_id` |
| `title` | string | 是 | `雨夜来信` | 场景标题 |
| `chapter_refs` | list[string] | 是 | `[ch01]` | 来源章节 |
| `location_ref` | string | 否 | `l001` | 地点 ID，样例中可省略 |
| `time_of_day` | string | 否 | `night` | 时间段 |
| `objective` | string | 是 | `姐姐林薇失踪已经七天...` | 场景目标 |
| `summary` | string | 否 | `林然循着匿名短信...` | 场景摘要 |
| `beats` | list[object] | 是 | `[]` | 场景节拍 |
| `transitions` | object | 否 | `{}` | 转场信息 |
| `source_refs` | list[object] | 是 | `[]` | 原文追溯 |

#### 5.7.1 `beats[]`

`beats` 是剧本正文的最小可编辑单元。

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `beat_id` | string | 是 | `b001` | 节拍 ID |
| `type` | enum | 是 | `action` | 节拍类型 |
| `text` | string | 是 | `铁门被暴力踹开...` | 正文内容 |
| `speaker_ref` | string | 否 | `c001` | 对白说话人，仅对白通常需要 |
| `emotion` | string | 否 | `angry` | 情绪标记，可为空字符串 |

`type` 推荐值：

- `action`：动作描写。
- `dialogue`：对白。
- `narration`：旁白或舞台提示。
- `transition`：转场文字。

#### 5.7.2 `transitions`

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `next_scene_hint` | string | 否 | `头顶钢架发出濒临断裂的呻吟...` | 指向下一场的衔接提示 |
| `transition_type` | string | 否 | `cut` | 转场类型 |

#### 5.7.3 `source_refs[]`

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `chapter_id` | string | 是 | `ch01` | 来源章节 ID |
| `excerpt_id` | string | 否 | `p001` | 来源切片 ID |

### 5.8 `quality`

类型：`object`

说明：记录当前草稿的质量判断和人工修订建议。

字段：

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `confidence` | number | 否 | `1.0` | 置信度 |
| `warnings` | list[string] | 否 | `[]` | 风险提示 |
| `revision_suggestions` | list[string] | 否 | `[建议人工复核关键对白...]` | 修订建议 |
| `continuity_checks` | object | 否 | `{}` | 连续性检查 |

`continuity_checks` 字段：

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `character_consistency` | boolean | `true` | 人物是否一致 |
| `timeline_consistency` | boolean | `true` | 时间线是否一致 |
| `location_consistency` | boolean | `true` | 地点是否一致 |
| `reference_consistency` | boolean | `true` | 原文引用是否一致 |

### 5.9 `extensions`

类型：`object`

说明：业务扩展层。核心 Schema 不应频繁变化，非核心但有价值的信息统一放入 `extensions`。

字段：

| 字段 | 类型 | 必填 | 示例 | 说明 |
|---|---|---:|---|---|
| `generator` | string | 否 | `ai-fiction-to-script` | 生成工具名 |
| `local_versioning` | boolean | 否 | `true` | 是否启用本地版本管理 |
| `ingestion` | object | 否 | `{}` | 输入处理信息 |
| `production_notes` | object | 否 | `{}` | 生产建议 |
| `regeneration_bundle` | object | 否 | `{}` | 重生成所需原文包 |

#### 5.9.1 `extensions.ingestion`

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `minimum_required_chapters` | integer | `3` | 最少章节要求 |
| `uploaded_input_ref` | string | `.novel2script\_uploads\老街回声_20260607085859.txt` | 上传原文引用 |
| `chapter_split_method` | string | `heading_based` | 切章方法 |

#### 5.9.2 `extensions.production_notes`

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `draft_stage` | string | `first_pass` | 草稿阶段 |
| `recommended_episode_count` | integer | `1` | 建议集数 |
| `recommended_runtime_minutes` | integer | `25` | 建议时长 |
| `review_owner` | string | `human_editor` | 审阅负责人 |

#### 5.9.3 `extensions.regeneration_bundle`

说明：保存重生成所需的原始章节文本。上传 YAML 后重生成整篇剧本时，可以从这里恢复输入上下文。

字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `source_chapters` | list[object] | 否 | 原始章节文本列表 |

`source_chapters[]` 字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `chapter_id` | string | 是 | 章节 ID |
| `title` | string | 是 | 章节标题 |
| `text` | string | 是 | 章节原文 |

## 6. 最小完整示例

下面示例压缩自 `老街回声_v0002.yaml`，用于说明主要层级关系：

```yaml
schema_version: "2.0"
meta:
  project_id: 老街回声
  title: 老街回声
  original_novel_title: 老街回声
  original_author: sun
  target_format: stage_play
  language: zh-CN
  genre:
    - 悬疑
  tone: angry
  created_at: "2026-06-07T08:58:59.436562+00:00"
  model_provider: qwen
  model_name: qwen3.6-flash

source:
  chapter_count: 3
  chapters:
    - chapter_id: ch01
      title: 第一章 雨夜来信
      raw_text_ref: .novel2script\_uploads\老街回声_20260607085859.txt
      summary: 林然在老街咖啡馆守到打烊，收到匿名短信。
      excerpt_count: 1

adaptation:
  adaptation_goal: 将小说改编为舞台剧剧本，强调台词张力、场面调度和有限空间表达。
  compression_strategy: merge_minor_events
  pacing_policy: preserve_key_conflicts
  structure_type: continuous_sequence
  style_guide:
    dialogue_style: 锋利压迫
    narration_style: 情绪强烈
    pacing_style: 急促

story_bible:
  logline: 老街回声围绕主要人物逐步揭开核心冲突并推动故事升级。
  synopsis: 林然追查姐姐林薇失踪真相，并与沈青、陈默发生冲突。
  theme:
    - 真相
  characters:
    - character_id: c001
      name: 林然
      role: protagonist
      traits:
        - 克制
        - 有目标
      goal: 推动主线发展
      conflict: 在追求目标时遭遇阻力
      arc: 从被动进入主动
      voice: 简洁直接
      relations: []
  locations:
    - location_id: l001
      name: 老街咖啡馆
      description: 与关键事件相关的地点
      mood: 悬而未决
  timeline:
    - event_id: e001
      time_order: 1
      summary: 林然收到匿名短信。
      chapter_refs:
        - ch01
  props:
    - 短信

outline:
  structure_type: continuous_sequence
  acts:
    - act_id: main
      name: 正文
      purpose: 按小说内容连续推进剧情，而不是套用固定三幕模板。
      scene_count: 3
  scene_plans:
    - scene_id: s001
      act_id: main
      title: 雨夜来信
      objective: 林然收到匿名短信并进入旧仓库。
      chapter_refs:
        - ch01
      conflict: 林然在追查姐姐失踪真相时遇到阻力。
      notes: 暴雨、昏黄灯光和逼仄空间强化悬疑。
      focus_event: 林然在老街咖啡馆守到打烊。
      bridge_in: ""
      bridge_out: 旧仓库在河堤后面，铁门半掩。

script:
  acts:
    - act_id: main
      title: 正文
      scenes:
        - scene_id: s001
          title: 雨夜来信
          chapter_refs:
            - ch01
          time_of_day: night
          objective: 林然收到匿名短信并进入旧仓库。
          summary: 林然循着匿名短信闯入废弃旧仓库。
          beats:
            - beat_id: b001
              type: action
              text: 铁门被暴力踹开，冷雨混着腥风灌满昏暗仓库。
              emotion: ""
            - beat_id: b002
              type: dialogue
              text: 滚出去！这里早就烂透了！
              speaker_ref: c001
              emotion: angry
          transitions:
            next_scene_hint: 头顶钢架发出濒临断裂的呻吟。
            transition_type: cut
          source_refs:
            - chapter_id: ch01
              excerpt_id: p001

quality:
  confidence: 1.0
  warnings: []
  revision_suggestions:
    - 建议人工复核关键对白，使角色口吻更鲜明。
  continuity_checks:
    character_consistency: true
    timeline_consistency: true
    location_consistency: true
    reference_consistency: true

extensions:
  generator: ai-fiction-to-script
  local_versioning: true
  ingestion:
    minimum_required_chapters: 3
    uploaded_input_ref: .novel2script\_uploads\老街回声_20260607085859.txt
    chapter_split_method: heading_based
  production_notes:
    draft_stage: first_pass
    recommended_episode_count: 1
    recommended_runtime_minutes: 25
    review_owner: human_editor
  regeneration_bundle:
    source_chapters:
      - chapter_id: ch01
        title: 第一章 雨夜来信
        text: 林然在老街咖啡馆守到打烊，窗外的雨把街灯晕成一片模糊的光。
```

## 7. 推荐校验规则

实现和测试中建议校验以下规则：

1. `schema_version` 必须存在，当前推荐值为 `"2.0"`。
2. `source.chapter_count == len(source.chapters)`。
3. `source.chapter_count >= extensions.ingestion.minimum_required_chapters`，样例为 `3`。
4. `source.chapters[].chapter_id` 必须唯一。
5. `story_bible.characters[].character_id` 必须唯一。
6. `story_bible.locations[].location_id` 必须唯一。
7. `outline.acts[].act_id` 必须唯一。
8. `outline.scene_plans[].scene_id` 必须唯一。
9. `script.acts[].act_id` 应能在 `outline.acts[].act_id` 中找到。
10. `script.acts[].scenes[].scene_id` 应能在 `outline.scene_plans[].scene_id` 中找到。
11. `chapter_refs` 中的章节 ID 必须来自 `source.chapters[].chapter_id`。
12. `source_refs[].chapter_id` 必须来自 `source.chapters[].chapter_id`。
13. `beats[].speaker_ref` 如果存在，必须来自 `story_bible.characters[].character_id`。
14. `location_ref` 如果存在，必须来自 `story_bible.locations[].location_id`。
15. `quality.continuity_checks` 应覆盖人物、时间线、地点和引用一致性。

## 8. 生成与重生成流程中的字段用途

### 8.1 首次生成

首次从小说生成剧本时，推荐流程是：

1. 从上传文本生成 `source`。
2. 根据章节摘要生成 `story_bible`。
3. 根据改编类型和风格生成 `adaptation`。
4. 规划 `outline`。
5. 生成 `script`。
6. 写入 `quality` 和 `extensions`。

### 8.2 上传 YAML 后整篇重生成

上传已有 YAML 后，系统应优先读取：

- `meta`
- `source`
- `adaptation`
- `story_bible`
- `outline`
- `extensions.regeneration_bundle.source_chapters`

其中 `regeneration_bundle.source_chapters[].text` 是恢复原始上下文的关键字段。如果该字段缺失，系统只能依赖摘要和已有剧本，重生成质量会下降。

### 8.3 单场景重生成

单场景重生成时，系统应读取：

- 当前 `scene_id`
- 对应的 `outline.scene_plans[]`
- 对应的 `script.acts[].scenes[]`
- 场景相关 `chapter_refs`
- `story_bible.characters`
- `story_bible.locations`
- `adaptation.style_guide`

重生成后应保持：

- `scene_id` 不变。
- `chapter_refs` 不丢失。
- `source_refs` 不丢失。
- 角色引用尽量继续使用已有 `character_id`。

## 9. 命名建议

推荐命名模式：

| 对象 | ID 示例 | 说明 |
|---|---|---|
| 章节 | `ch01` | 按原文顺序编号 |
| 人物 | `c001` | 按首次出现顺序编号 |
| 地点 | `l001` | 按首次出现顺序编号 |
| 时间线事件 | `e001` | 按故事时间顺序编号 |
| 幕 | `main` | 单幕连续结构可使用 `main` |
| 场景 | `s001` | 按剧本顺序编号 |
| 节拍 | `b001` | 每个场景内从 `b001` 重新编号 |
| 原文切片 | `p001` | 每个章节内从 `p001` 重新编号 |

## 10. 交付物建议

仓库建议同时维护：

1. 本规范文档：`AI-小说转剧本工具-YAML Schema规范.md`
2. JSON Schema：`schemas/screenplay.schema.json`
3. 示例 YAML：例如 `老街回声_v0002.yaml`

规范文档用于人工理解，JSON Schema 用于程序校验，示例 YAML 用于演示实际生成结果。
