---
name: download-engineering-standards
description: Use when 用户显式调用旧名称 download-engineering-standards 或工程标准规范下载；此名称兼容升级后的标准规范下载技能。
---

# 工程标准规范下载（旧名称兼容）

此技能已扩展为“标准规范下载”，主技能为 `download-standards`，覆盖各领域国内外标准，并保留工程专项核验。

收到旧名称调用时读取同级 [标准规范下载主技能](../download-standards/SKILL.md)，按主技能完整工作流处理；脚本及分领域参考以 `../download-standards/` 为根目录。没有主技能时报告安装缺件，不把旧工程版冒充完整升级版。

备份恢复时同时安装 `download-standards/` 与本兼容目录。新请求优先使用 `$download-standards`。
