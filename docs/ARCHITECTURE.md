# 架构设计

## 分层原则

工具严格拆成四层：

1. 输入理解层：章节切分、章节摘要、人物与事件抽取
2. 改编规划层：Story Bible、Outline、Scene Plan
3. 剧本生成层：逐场景生成 Beat、对白、动作和转场
4. 质量控制层：结构校验、引用校验、一致性检查、修复建议

## 模块边界

- `QwenClient`: 统一模型调用入口，屏蔽底层 API 差异
- `PromptBuilder`: 为每个阶段产出结构化提示词
- `ChapterParser`: 从原始小说文本中提取章节和清洗结果
- `StoryBuilder`: 汇总章节理解结果，构建 Story Bible
- `OutlinePlanner`: 生成三幕式/多场式结构
- `ScriptGenerator`: 逐场景生成剧本正文
- `QualityChecker`: 完成 Schema、引用和一致性校验
- `VersionStore`: 持久化每次产物、支持 diff 与回滚

## 扩展策略

- 模型扩展：保持 `AIClient` 抽象，新增模型供应商只需要实现同一接口
- 剧种扩展：由 `target_format`、`structure_type` 和 `style_guide` 驱动
- 输出扩展：内部先保留对象模型，最终再导出 YAML/JSON/Markdown
- 编排扩展：每个阶段输入输出固定，后续可接任务队列或 Web 前端

