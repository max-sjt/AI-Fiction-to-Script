# AI Fiction to Script

一个基于阿里通义千问（Qwen）的小说转剧本工具。它面向不少于 3 个章节的小说文本，按“理解 -> 规划 -> 生成 -> 校验”的流水线输出结构化、可编辑、可追溯的 YAML 剧本初稿。

## 当前版本

- `v0.2.0`
- 已完成：项目骨架、YAML Schema 数据模型、Qwen/Mock 编排链路、本地版本仓库、CLI
- 下一步：补充示例、测试、Schema 导出和场景级重生成

## 设计目标

- 用结构化输出代替一整段不可编辑文本
- 保留章节和片段来源，支持回溯与局部重写
- 让 Story Bible、Outline、Script、Quality 各阶段可独立演进
- 为后续接入 Web UI、任务队列、多剧种模板预留接口

## 目标输出

顶层 YAML 结构：

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

## 模块划分

- `models/`: Pydantic 数据模型和 Schema 基础约束
- `services/`: 文本解析、Qwen 调用、YAML 序列化、版本管理
- `pipeline/`: 任务编排与上下文流转
- `docs/`: 架构与 Schema 设计文档

## 文档

- [架构设计](docs/ARCHITECTURE.md)
- [YAML Schema 规范](docs/YAML_SCHEMA.md)
