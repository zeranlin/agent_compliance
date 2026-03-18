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

详细方案见：
- [法规原文本地存储方案](https://github.com/zeranlin/agent_compliance/blob/main/docs/design-docs/legal-authority-local-storage-spec.md)
