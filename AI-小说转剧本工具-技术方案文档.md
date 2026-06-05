# AI 小说转剧本工具 - 技术方案文档

## 1. 项目目标

构建一套基于阿里通义千问（Qwen）的多阶段小说改编引擎，实现：
- 小说理解
- 故事建模
- 剧本结构规划
- 场景级剧本生成
- YAML 序列化
- 结构校验与一致性修复

系统需支持长文本处理、局部重写、版本化输出和原文可追溯。

---

## 2. 总体技术路线

推荐采用“分层理解 + 分层生成 + 结构化校验”的流水线架构：

```text
输入小说文本
   ↓
章节切分与清洗
   ↓
章节摘要 / 角色抽取 / 事件抽取
   ↓
构建 Story Bible
   ↓
生成剧本 Outline
   ↓
逐场景生成 Script
   ↓
YAML 组装
   ↓
一致性与格式校验
   ↓
输出剧本初稿
```

---

## 3. 系统架构

### 3.1 前端层
负责：
- 小说上传
- 章节预览
- YAML 编辑器
- 场景列表
- 差异对比
- 再生成操作

### 3.2 服务层
负责：
- 任务编排
- 模型调用
- 中间结果存储
- YAML 生成与导出
- 一致性检查

### 3.3 AI 推理层
负责：
- 章节摘要
- 角色抽取
- 故事结构规划
- 场景内容生成
- 质量修复建议

### 3.4 存储层
负责：
- 原文存储
- 中间产物存储
- YAML 版本存储
- 任务状态存储

---

## 4. 功能模块设计

## 4.1 文本接入模块
### 职责
- 接收用户上传的小说文本
- 清洗无效字符
- 统一编码
- 自动识别章节标题和章节边界
- 检查章节数是否 >= 3

### 输出
- `chapters[]`
- 每章原文块
- 标准化文本

---

## 4.2 章节理解模块
### 职责
对每章进行语义理解，输出：
- 章节摘要
- 关键人物
- 关键事件
- 冲突点
- 情绪变化
- 场景变化

### 作用
为后续全书级建模提供基础材料。

---

## 4.3 故事圣经模块（Story Bible）
### 职责
构建全书统一知识底座：
- 人物卡
- 关系网
- 时间线
- 地点
- 道具
- 主题
- 风格信息

### 作用
保证跨场景、跨章节的一致性。

---

## 4.4 改编规划模块
### 职责
将小说结构映射为剧本结构：
- 三幕式 / 五场式 / 分集结构
- 场景划分
- 每场戏的目标
- 节奏控制
- 情节删减或合并建议

### 输出
- `outline`
- `scene_plan[]`

---

## 4.5 剧本生成模块
### 职责
按场景生成：
- 场景标题
- 场景描述
- 动作
- 台词
- 转场
- 节拍（Beat）

### 输出
- `script.acts[].scenes[]`

---

## 4.6 一致性校验模块
### 职责
检查：
- YAML 格式是否合法
- 角色命名是否统一
- 时间线是否冲突
- 地点跳跃是否合理
- 事件因果是否完整
- 台词是否符合角色口吻

### 输出
- `quality.warnings[]`
- `quality.confidence`
- `quality.revision_suggestions[]`

---

## 4.7 YAML 组装模块
### 职责
将内部对象结构序列化为 YAML。

### 原则
- 内部推荐使用对象 / JSON 结构
- 最终再导出为 YAML
- 便于程序校验和编辑器渲染

---

## 4.8 编辑与再生成模块
### 职责
- 支持用户修改任意字段
- 支持单场重写
- 支持角色口吻重写
- 支持版本管理与对比

---

## 5. Qwen 模型调用方案

建议按能力分工，不要用单次调用完成全部任务。

### 5.1 Qwen-Max
用于：
- 全局改编规划
- 复杂剧情理解
- 场景生成
- 冲突修复

### 5.2 Qwen-Plus
用于：
- 章节摘要
- 人物抽取
- 关系抽取
- 中间结构整理

### 5.3 Qwen-Turbo
用于：
- 文本清洗
- 章节识别辅助
- 结构校验辅助
- 轻量级修复建议

---

## 6. AI 编排策略

建议采用四段式链路：

### 阶段 1：理解
输入原文，输出：
- 章节摘要
- 人物列表
- 事件链
- 主题摘要

### 阶段 2：规划
输入理解结果，输出：
- Story Bible
- 剧本结构
- 场景规划

### 阶段 3：生成
按场景逐个生成：
- 动作
- 对白
- 节奏
- 转场

### 阶段 4：校验与修复
检查：
- 一致性
- YAML 合法性
- 逻辑断层
- 风格偏差

---

## 7. 数据模型设计

### 7.1 顶层结构
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

### 7.2 字段说明

#### 1）`schema_version`
- 类型：`string`
- 作用：Schema 版本控制
- 原因：便于未来升级与兼容

#### 2）`meta`
- 类型：`object`
- 内容：标题、作者、剧种、语言、模型信息
- 原因：便于项目管理与追踪

#### 3）`source`
- 类型：`object`
- 内容：章节数、章节标题、原文引用
- 原因：支持追溯原文、支持局部重写

#### 4）`adaptation`
- 类型：`object`
- 内容：改编目标、风格策略、压缩策略
- 原因：明确“如何改编”，而不只是“改什么”

#### 5）`story_bible`
- 类型：`object`
- 内容：人物、关系、地点、时间线、主题
- 原因：保持全局一致性

#### 6）`outline`
- 类型：`object`
- 内容：幕结构、场景分配、节奏安排
- 原因：先搭骨架，再填内容

#### 7）`script`
- 类型：`object`
- 内容：实际剧本内容
- 原因：可编辑、可拆分、可重生成

#### 8）`quality`
- 类型：`object`
- 内容：置信度、警告、修复建议
- 原因：让 AI 结果可审阅、可修复

#### 9）`extensions`
- 类型：`object`
- 内容：预留扩展字段
- 原因：提高 Schema 的长期适应性

---

## 8. YAML Schema 设计原因说明

### 8.1 为什么分层设计
小说转剧本不是单步转换，而是：
- 原文理解
- 故事抽象
- 结构规划
- 场景生成
- 质量修正

分层后，每一层都可独立修改和重跑。

### 8.2 为什么使用 ID 引用
例如 `character_id`、`scene_id`、`location_id`。

原因：
- 名字可能重复或修改
- ID 稳定，便于引用和校验
- 便于构建关系图和版本管理

### 8.3 为什么保留 `source_refs`
原因：
- 便于溯源到原小说章节
- 便于作者检查改编是否忠实
- 便于局部重生成

### 8.4 为什么增加 `quality`
原因：
- AI 输出并非天然完全正确
- 显式标记问题比隐藏错误更重要
- 便于作者优先处理高风险内容

### 8.5 为什么保留 `extensions`
原因：
- 后续可能支持不同剧种
- 不同业务方有自定义字段需求
- 避免频繁破坏兼容性

---

## 9. 推荐 YAML 示例

```yaml
schema_version: "1.0"
meta:
  title: "老街回声"
  original_novel_title: "老街回声"
  original_author: "某某"
  target_format: "tv_drama"
  language: "zh-CN"
  model_provider: "qwen"
  model_name: "qwen-max"

source:
  chapter_count: 3
  chapters:
    - chapter_id: "ch01"
      title: "第一章"
      summary: "主角得知姐姐失踪。"
    - chapter_id: "ch02"
      title: "第二章"
      summary: "主角追查线索。"
    - chapter_id: "ch03"
      title: "第三章"
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
  theme: ["亲情", "真相", "成长"]
  characters:
    - character_id: "c001"
      name: "林然"
      role: "protagonist"
      traits: ["倔强", "克制"]

outline:
  structure_type: "three_act"
  acts:
    - act_id: "a1"
      name: "开端"
      purpose: "发现异常"

script:
  acts:
    - act_id: "a1"
      title: "开端"
      scenes:
        - scene_id: "s001"
          title: "咖啡馆初见"
          chapter_refs: ["ch01", "ch02"]
          objective: "触发主角行动"
          beats:
            - beat_id: "b001"
              type: "action"
              text: "林然推门进入咖啡馆。"
            - beat_id: "b002"
              type: "dialogue"
              speaker_ref: "c001"
              text: "你到底知道什么？"

quality:
  confidence: 0.91
  warnings: []
  continuity_checks:
    character_consistency: true
    timeline_consistency: true
    location_consistency: true
```

---

## 10. 技术栈建议

### 10.1 前端
- React / Vue
- YAML 编辑器组件
- Diff 对比组件
- 任务进度展示

### 10.2 后端
- Python FastAPI 或 Node.js NestJS
- 任务队列：Celery / BullMQ
- 模型编排服务

### 10.3 存储
- 原文与中间结果：对象存储 / 文件存储
- 结构化数据：MySQL / PostgreSQL
- 缓存：Redis

### 10.4 AI 接口
- 阿里通义千问 Qwen 系列模型
- 采用多模型分工策略

---

## 11. 接口设计建议

### 11.1 创建改编任务
`POST /api/adaptations`

输入：
- 小说文本
- 项目名称
- 改编类型
- 目标风格

输出：
- `task_id`

### 11.2 查询任务状态
`GET /api/adaptations/{task_id}`

输出：
- 当前步骤
- 进度百分比
- 失败信息
- 中间产物

### 11.3 获取 YAML 结果
`GET /api/adaptations/{task_id}/script`

输出：
- YAML 文本
- 结构化对象

### 11.4 局部重生成
`POST /api/adaptations/{task_id}/regenerate`

输入：
- 场景 ID
- 修改要求

输出：
- 新版本场景

---

## 12. 任务编排建议

建议将整个过程拆成异步任务链：

1. 文本清洗
2. 章节切分
3. 章节理解
4. 故事圣经生成
5. 改编规划
6. 场景生成
7. 质量校验
8. YAML 输出

这样做的好处：
- 可恢复
- 可重试
- 可单步调试
- 适合长文本和复杂改编任务

---

## 13. 风险与应对

### 13.1 长文本上下文丢失
**应对**：采用分章节处理 + Story Bible 汇总，不依赖单次长上下文。

### 13.2 人物前后不一致
**应对**：所有场景生成前加载统一人物卡。

### 13.3 剧本结构松散
**应对**：先生成 Outline，再生成场景正文。

### 13.4 YAML 不合法
**应对**：生成后做 Schema 校验与自动修复。

### 13.5 改编过于照抄小说
**应对**：在规划阶段加入压缩、重组、冲突强化策略。

---

## 14. 里程碑建议

### 第一阶段：MVP
- 小说输入
- 章节识别
- Story Bible
- 基础 YAML 输出

### 第二阶段：增强版
- 场景级编辑
- 局部重写
- 质量提示
- 版本对比

### 第三阶段：专业版
- 多剧种模板
- 风格模板库
- 分集规划
- 批量改编
- 团队协作

---

## 15. 结论

该技术方案的核心思想是：

- **产品上**：让小说作者快速获得可编辑的剧本初稿
- **技术上**：用 Qwen 构建“理解 → 规划 → 生成 → 校验”的分层 AI 编排
- **数据上**：用 YAML Schema 标准化剧本结构，保证可读、可改、可追溯
- **工程上**：采用模块化设计，方便后续扩展不同剧种、风格和编辑能力
```