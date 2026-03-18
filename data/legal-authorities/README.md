# 本地法规原文快照目录

本目录用于存放离线可用的法规原文快照、标准化文本和索引文件。

当前约定：
- `raw/`：原始快照层，例如 PDF、HTML、正文页及其 `metadata.json`
- `normalized/`：从原始快照提取出的稳定文本
- `index/`：供代码检索层读取的索引文件

当前状态：
- 已建立目录和样板元数据
- 尚未批量下载权威原文
- `LEGAL-001`、`LEGAL-002` 已建立快照元数据样板和标准化文本入口
- 已生成第一版 `index/clause-index.json`，把最常用两份法规抽成条文级索引，供后续 `legal_clause_index` 和法规语义推理层使用

详细方案见：
- [法规原文本地存储方案](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/legal-authority-local-storage-spec.md)
- [法规条文级语义层设计方案](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/legal-semantic-layer-design.md)
