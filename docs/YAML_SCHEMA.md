# YAML Schema 规范

本工具输出的剧本初稿必须符合统一 Schema，核心目标有四个：

- 可编辑：作者可以直接修改任意字段
- 可追溯：场景和节拍能映射回原小说章节
- 可校验：程序可以自动检查结构和引用是否合法
- 可扩展：支持不同剧种和后续新字段演进

## 顶层结构

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

## 设计原因

### 为什么分层

小说改编不是一次性吐出完整剧本，而是：

1. 先理解原文
2. 再抽象故事知识底座
3. 再规划剧本结构
4. 最后生成场景正文并校验

分层后可以只重跑局部阶段，不需要每次都从头生成。

### 为什么统一用 ID

人物、地点、章节、场景都用稳定 ID，而不是只依赖中文名称：

- 名称可能修改
- 名称可能重复
- 稳定 ID 更适合版本管理和引用校验

### 为什么保留 `source_refs`

- 便于追溯具体来源章节
- 便于作者核对改编忠实度
- 便于局部重生成和定点修改

### 为什么保留 `quality`

- AI 初稿天然存在不确定性
- 问题显式化比隐藏错误更重要
- 方便后续自动修复和人工复核

## 实现位置

- Pydantic 模型：`src/ai_fiction_to_script/models/schema.py`
- JSON Schema 导出：后续版本提供到 `schemas/screenplay.schema.json`

