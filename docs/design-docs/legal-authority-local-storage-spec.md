# 法规原文本地存储方案

## 目标

为政府采购合规审查系统补齐“权威原文快照层”，使系统在无网络环境下仍可：
- 使用本地权威法规原文进行检索和引用
- 使用本地标准化文本进行条文级抽取
- 对已下载资料进行有效性留痕和版本追溯

本方案解决的问题不是“是否能跑审查”，而是“断网时能否继续使用权威法规原文，而不只依赖摘要型引用资料”。

## 当前状态

当前仓库已经具备两层资料：

1. 引用摘要与元数据层
- 目录：`docs/references/legal-authorities/`
- 作用：保存法规摘要、适用主题、来源链接、位阶、核验说明

2. 权威目录核验层
- 例如：[财政部规章](https://www.ccgp.gov.cn/zcfg/mofgz/)
- 作用：用于核验财政部规章的令号、有效性和目录归属

当前仍缺少：

3. 权威原文快照层
- 本地保存 PDF、HTML、正文页或规范化文本

4. 标准化文本层
- 从原文快照提取稳定文本，供离线检索、摘录和规则映射使用

## 总体设计

建议把法规资料分为四层：

### 第一层：引用摘要层

目录：
- `docs/references/legal-authorities/*.md`

职责：
- 人工可读
- 审查主题说明
- 法律位阶与引用说明
- 原始来源链接
- 权威目录核验信息

### 第二层：原文快照层

建议目录：
- `data/legal-authorities/raw/`

建议按 `reference_id` 建子目录，例如：

```text
data/legal-authorities/raw/
  LEGAL-001/
    source.pdf
    metadata.json
  LEGAL-002/
    source.html
    metadata.json
```

职责：
- 保存权威来源的原始快照
- 支持断网时继续访问原文
- 保留下载时间、原始链接、校验值

### 第三层：标准化文本层

建议目录：
- `data/legal-authorities/normalized/`

例如：

```text
data/legal-authorities/normalized/
  LEGAL-001.txt
  LEGAL-002.txt
```

职责：
- 把 PDF/HTML/正文页统一转成稳定文本
- 便于代码离线检索和条文级摘录
- 便于后续条款定位和引用抽取

### 第四层：索引与映射层

建议目录：
- `data/legal-authorities/index/`

例如：

```text
data/legal-authorities/index/
  authorities.json
  topic_to_authority.json
```

职责：
- 为代码检索层提供统一入口
- 映射 `reference_id -> snapshot -> normalized_text -> review_topics`

## 原文快照元数据

建议每份 `metadata.json` 至少包含：

```json
{
  "reference_id": "LEGAL-001",
  "source_url": "https://gks.mof.gov.cn/...",
  "canonical_registry_url": "https://www.ccgp.gov.cn/zcfg/mofgz/",
  "doc_no": "财库〔2021〕22号",
  "authority_level": "部门规范性文件",
  "validity_status": "有效",
  "downloaded_at": "2026-03-18T10:00:00+08:00",
  "snapshot_format": "pdf",
  "snapshot_path": "data/legal-authorities/raw/LEGAL-001/source.pdf",
  "snapshot_sha256": "待填充",
  "normalized_text_path": "data/legal-authorities/normalized/LEGAL-001.txt",
  "last_registry_verified": "2026-03-18",
  "verification_source": "财政部官网原文"
}
```

## 代码使用优先级

后续代码检索层建议按以下顺序取资料：

1. 优先读取本地标准化文本
- 用于离线检索、关键词定位、摘录生成

2. 其次读取本地摘要型引用资料
- 用于审查主题说明、位阶说明、规则映射

3. 有网时再进行权威目录核验
- 核验是否有效
- 核验令号、文号、原始来源是否变化

## 与当前代码链路的关系

当前代码链路读取的是：
- `docs/references/legal-authorities/*.md`

当前还未读取：
- `data/legal-authorities/raw/**`
- `data/legal-authorities/normalized/**`

所以这份方案落地后，后续代码需要新增两类能力：

1. 权威原文快照读取器
- 根据 `reference_id` 定位本地快照

2. 标准化文本优先检索器
- 审查时优先使用本地标准化法规文本

## 适用范围

优先适用于：
- 法律
- 行政法规
- 财政部规章
- 财政部规范性文件
- 财政部办公厅文件

其中应特别区分：
- 财政部规章可以使用中国政府采购网“财政部规章”目录页作为核验层
- 办公厅通知、规范性文件一般应使用财政部官网原文作为核验层

## 落地顺序建议

### 阶段一：结构先落地

完成：
- 建立 `data/legal-authorities/raw/`
- 建立 `data/legal-authorities/normalized/`
- 建立 `data/legal-authorities/index/`
- 明确 `metadata.json` 字段

### 阶段二：样板资料入库

先选少量高频资料：
- `LEGAL-001`
- `LEGAL-002`

完成：
- 保存原文快照
- 生成标准化文本
- 建立索引

### 阶段三：代码检索接入

完成：
- 让 `references_index.py` 支持读取本地标准化文本和快照元数据
- 审查时优先使用本地标准化原文

### 阶段四：核验与更新

完成：
- 有网时按目录页和官网原文复核有效性
- 变更后更新 `metadata.json`

## 当前结论

当前仓库已经有：
- 离线可用的摘要型法规引用层
- 权威目录核验规范

当前仓库还没有：
- 本地权威原文快照层
- 本地标准化法规文本层

如果目标是“无网环境下仍能稳定使用权威法规原文支撑代码审查”，则应按本方案继续落地。
