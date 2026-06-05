# AI 小说转剧本工具 - YAML Schema 规范

## 1. 文档目的

本文档用于定义“AI 小说转剧本工具”输出剧本初稿的 YAML 数据结构规范。该规范的目标是让小说改编结果具备：

- **结构化**：便于程序解析、校验与渲染
- **可编辑**：便于作者进行人工修改
- **可追溯**：便于回溯原小说章节与片段
- **可扩展**：便于支持不同剧种与未来功能演进
- **可校验**：便于自动检查结构合法性与一致性

该 Schema 适用于小说文本达到 **3 个章节及以上** 的改编任务，输出对象为可编辑的剧本初稿，而非最终定稿。

---

## 2. 设计原则

### 2.1 分层表达
将“小说理解”“改编规划”“剧本正文”“质量控制”拆分为不同层级，避免把所有信息混在一处。

### 2.2 引用优先
人物、地点、场景、事件统一使用 ID 引用，而不是仅靠名称匹配。

### 2.3 可追溯
每个场景、节拍、台词尽量保留来源章节或原文引用信息。

### 2.4 可扩展
预留 `extensions` 字段，支持不同业务场景的自定义扩展。

### 2.5 可校验
所有核心字段均应有明确类型与约束，便于程序进行结构校验。

---

## 3. 顶层结构

建议顶层结构如下：

```yaml
schema_version: "1.0"
meta: {}
source: {}
adaptation: {}
story_bible: {}
outline: {}
script: {}
quality: {}
extensions: {}
```

---

## 4. 顶层字段定义

## 4.1 `schema_version`

### 类型
`string`

### 说明
用于标识当前 YAML Schema 的版本号。

### 示例
```yaml
schema_version: "1.0"
```

### 设计原因
- 便于未来升级 Schema
- 避免字段变更导致旧数据失效
- 支持版本迁移与兼容处理

---

## 4.2 `meta`

### 类型
`object`

### 说明
记录项目基础信息、输出目标与模型信息。

### 推荐字段
```yaml
meta:
  project_id: "novel2script_001"
  title: "老街回声"
  original_novel_title: "老街回声"
  original_author: "某某"
  target_format: "tv_drama"
  language: "zh-CN"
  genre: ["悬疑", "成长"]
  tone: "克制"
  created_at: "2026-06-05T10:00:00Z"
  model_provider: "qwen"
  model_name: "qwen-max"
```

### 设计原因
- 便于项目管理和版本追踪
- 便于根据剧种选择不同输出模板
- 便于记录模型来源与生成上下文

---

## 4.3 `source`

### 类型
`object`

### 说明
记录小说原文来源与章节信息。

### 推荐字段
```yaml
source:
  chapter_count: 5
  chapters:
    - chapter_id: "ch01"
      title: "第一章"
      raw_text_ref: "source/ch01.txt"
      summary: "本章摘要"
    - chapter_id: "ch02"
      title: "第二章"
      raw_text_ref: "source/ch02.txt"
      summary: "本章摘要"
```

### 设计原因
- 支持原文追溯
- 支持章节级重生成
- 支持判断输入是否满足“3 章以上”要求

---

## 4.4 `adaptation`

### 类型
`object`

### 说明
记录改编策略与风格规则。

### 推荐字段
```yaml
adaptation:
  adaptation_goal: "将小说改编为可编辑剧本初稿"
  compression_strategy: "merge_minor_events"
  pacing_policy: "preserve_key_conflicts"
  style_guide:
    dialogue_style: "自然口语化"
    narration_style: "简洁"
```

### 设计原因
- 不同小说可采用不同改编策略
- 显式记录改编目标，方便 AI 按要求生成
- 便于后续调整整体风格，而不是重新设计整套系统

---

## 4.5 `story_bible`

### 类型
`object`

### 说明
全书统一知识底座，记录人物、地点、时间线、主题等全局信息。

### 推荐字段
```yaml
story_bible:
  logline: "一句话故事概述"
  synopsis: "全书梗概"
  theme: ["亲情", "真相", "成长"]
  characters:
    - character_id: "c001"
      name: "林然"
      role: "protagonist"
      traits: ["倔强", "克制"]
      goal: "寻找姐姐失踪的真相"
      conflict: "既想追查真相，又害怕揭开家庭秘密"
      arc: "从逃避到面对"
      voice: "短句、克制、略带自嘲"
      relations:
        - target_character_id: "c002"
          relation: "朋友"
  locations:
    - location_id: "l001"
      name: "老街咖啡馆"
      description: "狭长空间，灯光昏黄"
      mood: "安静、压抑"
  timeline:
    - event_id: "e001"
      time_order: 1
      summary: "林然得知姐姐失踪"
```

### 设计原因
- 保证跨章节、跨场景一致性
- 统一人物口吻与行为逻辑
- 支撑场景生成与质量校验

---

## 4.6 `outline`

### 类型
`object`

### 说明
记录剧本结构骨架，如三幕式、五场式或分集结构。

### 推荐字段
```yaml
outline:
  structure_type: "three_act"
  acts:
    - act_id: "a1"
      name: "开端"
      purpose: "建立人物关系与核心冲突"
      scene_count: 3
    - act_id: "a2"
      name: "发展"
      purpose: "冲突升级"
      scene_count: 5
    - act_id: "a3"
      name: "结局"
      purpose: "解决主要矛盾"
      scene_count: 2
```

### 设计原因
- 剧本改编需要先搭骨架，再填内容
- 便于作者快速理解全局节奏
- 方便后续结构重排

---

## 4.7 `script`

### 类型
`object`

### 说明
剧本正文主体，按幕、场景、节拍组织。

### 推荐层级
- Act（幕）
- Scene（场景）
- Beat（戏剧节拍）
- Dialogue / Action / Transition（具体内容）

### 推荐字段示例
```yaml
script:
  acts:
    - act_id: "a1"
      title: "开端"
      scenes:
        - scene_id: "s001"
          title: "咖啡馆初见"
          chapter_refs: ["ch01", "ch02"]
          location_ref: "l001"
          time_of_day: "night"
          objective: "触发主角行动"
          summary: "林然在咖啡馆收到匿名信息。"
          beats:
            - beat_id: "b001"
              type: "action"
              text: "林然推门进入咖啡馆，四下张望。"
            - beat_id: "b002"
              type: "dialogue"
              speaker_ref: "c001"
              text: "你到底知道什么？"
            - beat_id: "b003"
              type: "action"
              text: "手机震动，一条匿名短信跳出。"
          transitions:
            next_scene_hint: "林然开始追查短信来源"
          source_refs:
            - chapter_id: "ch01"
              excerpt_id: "p014"
            - chapter_id: "ch02"
              excerpt_id: "p006"
```

### 设计原因
- 场景级结构便于局部修改和再生成
- Beat 级结构适合控制节奏与戏剧冲突
- `source_refs` 让改编结果可回溯原文

---

## 4.8 `quality`

### 类型
`object`

### 说明
记录质量评估结果、一致性检查结果与修复建议。

### 推荐字段
```yaml
quality:
  confidence: 0.86
  warnings:
    - "人物B在第二场与第三场称谓不一致"
    - "第5场地点跳转较快，建议补充过场"
  continuity_checks:
    character_consistency: true
    timeline_consistency: true
    location_consistency: true
  revision_suggestions:
    - "加强主角与反派首次对话的冲突感"
```

### 设计原因
- 让 AI 输出“可用但可修”的初稿
- 显式暴露潜在问题，便于作者优先处理
- 便于后续自动修复或人工二次打磨

---

## 4.9 `extensions`

### 类型
`object`

### 说明
预留扩展字段，用于业务自定义或未来功能扩展。

### 示例
```yaml
extensions:
  custom_tags:
    adaptation_mode: "fast_draft"
    target_platform: "web_novel"
```

### 设计原因
- 降低 Schema 频繁变更的成本
- 支持不同剧种、不同业务场景的扩展需求
- 保持兼容性与长期演进能力

---

## 5. 字段关系说明

### 5.1 `source` 与 `script`
`source` 负责记录小说原始来源，`script` 负责记录改编后的场景内容。两者之间通过 `chapter_refs`、`source_refs` 形成映射关系。

### 5.2 `story_bible` 与 `script`
`story_bible` 统一定义人物、地点、时间线等全局信息，`script` 中通过 ID 引用这些对象，避免重复定义与前后不一致。

### 5.3 `outline` 与 `script`
`outline` 是剧本结构骨架，`script` 是具体填充内容。两者分离后便于先调整结构，再生成正文。

### 5.4 `quality` 与其余字段
`quality` 不是单独输出的附属内容，而是对前面所有阶段的检测结果汇总，帮助用户快速发现问题。

---

## 6. 字段命名规范

### 6.1 命名风格
- 使用小写英文 + 下划线或驼峰风格保持一致
- 建议整体采用 `snake_case`

### 6.2 ID 规范
- 所有实体 ID 必须稳定、唯一、可读
- 建议前缀区分类型：
  - `ch01`：章节
  - `c001`：角色
  - `l001`：地点
  - `a1`：幕
  - `s001`：场景
  - `b001`：节拍

### 6.3 文本规范
- 字符串字段应尽量简洁明确
- 对白字段应避免夹带结构说明
- 描述字段应与剧情直接相关

---

## 7. 校验规则建议

### 7.1 必填项校验
至少需要检查以下字段是否存在：
- `schema_version`
- `meta.title`
- `source.chapter_count`
- `story_bible.characters`
- `outline.acts`
- `script.acts`

### 7.2 类型校验
- 字符串字段必须是 string
- 数组字段必须是 array
- 对象字段必须是 object
- 布尔值字段必须是 boolean
- 数值字段必须是 number

### 7.3 引用校验
- `speaker_ref` 必须能在 `story_bible.characters` 中找到
- `location_ref` 必须能在 `story_bible.locations` 中找到
- `chapter_refs` 必须存在于 `source.chapters` 中

### 7.4 一致性校验
- 人物名称不能前后不一致
- 时间线不能出现明显冲突
- 同一场景的地点不应无理由跳变
- 场景目标应与节拍内容一致

---

## 8. 推荐扩展字段

可根据业务需要在 `extensions` 中扩展：

```yaml
extensions:
  target_audience: "young_adult"
  platform_constraints:
    max_scene_length: 1200
  style_reference: "现实主义悬疑"
  manual_review_required: true
```

扩展字段的原则是：**不破坏主 Schema 的兼容性**。

---

## 9. 完整示例

```yaml
schema_version: "1.0"
meta:
  project_id: "novel2script_001"
  title: "老街回声"
  original_novel_title: "老街回声"
  original_author: "某某"
  target_format: "tv_drama"
  language: "zh-CN"
  genre: ["悬疑", "成长"]
  tone: "克制"
  created_at: "2026-06-05T10:00:00Z"
  model_provider: "qwen"
  model_name: "qwen-max"

source:
  chapter_count: 3
  chapters:
    - chapter_id: "ch01"
      title: "第一章"
      raw_text_ref: "source/ch01.txt"
      summary: "主角得知姐姐失踪。"
    - chapter_id: "ch02"
      title: "第二章"
      raw_text_ref: "source/ch02.txt"
      summary: "主角追查线索。"
    - chapter_id: "ch03"
      title: "第三章"
      raw_text_ref: "source/ch03.txt"
      summary: "主角进入旧街区。"

adaptation:
  adaptation_goal: "将小说改编为可编辑剧本初稿"
  compression_strategy: "merge_minor_events"
  pacing_policy: "preserve_key_conflicts"
  style_guide:
    dialogue_style: "自然口语化"
    narration_style: "简洁"

story_bible:
  logline: "一个年轻人追查姐姐失踪真相，逐步揭开家庭秘密。"
  synopsis: "林然在追查姐姐失踪真相的过程中，逐渐发现家族秘密与旧街区中的隐秘联系。"
  theme: ["亲情", "真相", "成长"]
  characters:
    - character_id: "c001"
      name: "林然"
      role: "protagonist"
      traits: ["倔强", "克制"]
      goal: "寻找姐姐失踪的真相"
      conflict: "既想追查真相，又害怕面对家庭秘密"
      arc: "从逃避到面对"
      voice: "短句、克制、略带自嘲"
  locations:
    - location_id: "l001"
      name: "老街咖啡馆"
      description: "狭长空间，灯光昏黄"
      mood: "安静、压抑"
  timeline:
    - event_id: "e001"
      time_order: 1
      summary: "林然得知姐姐失踪"

outline:
  structure_type: "three_act"
  acts:
    - act_id: "a1"
      name: "开端"
      purpose: "建立人物关系与核心冲突"
      scene_count: 1

script:
  acts:
    - act_id: "a1"
      title: "开端"
      scenes:
        - scene_id: "s001"
          title: "咖啡馆初见"
          chapter_refs: ["ch01", "ch02"]
          location_ref: "l001"
          time_of_day: "night"
          objective: "触发主角行动"
          summary: "林然在咖啡馆收到匿名信息。"
          beats:
            - beat_id: "b001"
              type: "action"
              text: "林然推门进入咖啡馆，四下张望。"
            - beat_id: "b002"
              type: "dialogue"
              speaker_ref: "c001"
              text: "你到底知道什么？"
          source_refs:
            - chapter_id: "ch01"
              excerpt_id: "p014"

quality:
  confidence: 0.91
  warnings: []
  continuity_checks:
    character_consistency: true
    timeline_consistency: true
    location_consistency: true
  revision_suggestions:
    - "补充林然与匿名信息之间的情绪过渡"

extensions:
  target_audience: "young_adult"
  platform_constraints:
    max_scene_length: 1200
  style_reference: "现实主义悬疑"
  manual_review_required: true
```

---

## 10. 总结

本 Schema 的核心是把小说改编过程拆分为“理解、规划、生成、校验”四个层次，并通过 YAML 的结构化表达方式，将剧本初稿做成**可编辑、可追溯、可扩展、可验证**的数据对象。

这样既方便作者直接修改，也方便后续系统化处理，例如：
- 局部重生成
- 版本对比
- 自动校验
- 场景级重写
- 扩展到不同剧种

如果后续需要更强的兼容性，可在 v2 中继续增加：
- 分集结构
- 分镜扩展
- 角色关系图谱
- 风格模板引用
- 多版本并行管理
