# 标准规范下载 · Download Standards

用于Codex的标准规范查找、获取与核验技能。输入标准号、名称、链接或批量清单，尽力取得可追溯的完整原文件；取不到时，说明实际障碍、可阅读范围及其他获取渠道。

覆盖各领域的国家、行业、地方、团体、企业、国际和国外标准，以及技术规程和开放协议规范。“全部”指处理范围不限工程领域，不代表所有规范都能免费、无水印下载。

## 功能

- **实时版本核对**：查正式题录、发布及修订公告，区分当前有效版、已发布未实施版、历史版、草案和预览。
- **尽力寻找全文**：官方平台和附件 → 发布机构或授权出版社 → 可核验公开副本 → 允许保存的完整阅读内容。
- **实际获取文件**：检查附件、嵌入阅读器及页面实际使用的文件地址，正常请求、下载或浏览器保存。
- **全文核验**：检查真实格式、文档头、版次、目录、连续页/全部章节、末页、附录及电子附件。解析通过不自动等于已核验。
- **保留原件与质量信息**：PDF优先，原生Word可交付；官方HTML/TXT/XML等可保留原件，另做PDF时标阅读副本。默认不将PDF转Word。
- **修订与批量处理**：修改单、勘误和补遗单独交付，一个项目失败不阻断其他明确项目。国内采标版、国际原版和国家采纳版分别核验。

保留建筑、市政、交通、水利、电力工程专项，新增食品、卫生、医药、机械、电子、通信、环境、农业、金融、管理体系、服务及国际/国外路由。未列出的体系按实际发布机构继续查找。

## 安装

在Codex里提出：

> 使用 skill-installer 从 Aegean1218/download-standards 安装 download-standards；如果还需要旧名称，也安装 download-engineering-standards。

也可手动安装。macOS/Linux示例：

```sh
git clone https://github.com/Aegean1218/download-standards.git
cd download-standards
python3 - <<'PY'
import os, shutil
from pathlib import Path
skills_dir = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'skills'
skills_dir.mkdir(parents=True, exist_ok=True)
for name in ('download-standards', 'download-engineering-standards'):
    target = skills_dir / name
    if target.exists():
        raise SystemExit(f'{target} 已存在，请先备份并移出后再安装')
for name in ('download-standards', 'download-engineering-standards'):
    shutil.copytree(name, skills_dir / name)
print('安装完成')
PY
```

主技能可独立安装；旧名称兼容入口需要与主技能同级。Windows可手动复制两个目录到Codex技能目录。已有同名技能先备份。[详细安装、更新和依赖](docs/installation.md)。技能在下一轮或新会话可用；Python依赖仅运行辅助脚本时需要。

## 使用示例

直接提出需求，或显式调用 `$download-standards`：

```text
使用 $download-standards 下载 JT/T 1516-2024 完整正式PDF，核对版本和附录。
下载 GB 2760 当前有效版，附修改单，优先官方原文件。
找 ISO/IEC 27001 最新正式发布版；有官方中文版优先，没有就保留官方原文。
批量获取清单中的国标、团标和ASTM标准，逐项说明实际结果。
这个规范能在线看，检查能否正常保存原PDF；只能生成阅读副本时标注。
先找一下脚手架相关规范，我选定后再下载。
```

地方标准尽量附地区，企业内部规范附公司名或编号，国外标准可附版次、语言和分册。歧义项目单独待澄清，明确项目继续。

旧调用 `$download-engineering-standards` 保留兼容，进入新版流程；主技能允许自然语言自动触发，兼容入口仅显式调用。

## 结果与交付

默认当前工作区 `outputs/` 保存文件和中文核验记录，临时文件在 `work/`。

| 状态 | 含义 |
|---|---|
| 已下载并核验 | 身份、版本有正式证据，文件可打开，完整结构已检查 |
| 已下载待核验 | 已取得文件，但身份、版本或完整性仍有未确认项 |
| 仅可在线阅读 | 实测可读，未取得可保存的完整文件；注明全文/预览范围 |
| 需登录或购买 | 已确认入口需尚未具备的权限，未取得可靠公开全文 |
| 未找到 | 实际尝试路线无可靠目标或可用入口 |
| 待澄清 / 未执行 | 缺必要信息，或仅候选、尚未选择、尚未检索 |

记录来源链接、版本证据、大小、页数（适用时）、SHA-256、完整性和水印。指纹只证明保存字节可追踪，不证明权威、完整或最新。[工作流程与脚本用法](docs/workflow.md)。

## 获取边界与许可范围

优先原本无水印的完整文件，准确有水印原件优于错误或缺页的无水印副本。保持原貌，不删除、遮挡或裁掉水印。

登录、验证码、付费或禁止保存时，记录障碍并继续其他公开/已授权渠道；不绕过限制、不自动购买、不提取账号凭据。能在线阅读不保证能取得原生PDF。逐页内容须完整、有权访问且允许保存，生成后明确标为阅读副本。

本仓库发布技能、辅助代码和文档，不打包或再分发下载的标准正文。MIT许可证仅覆盖本仓库原创内容，标准全文和第三方依赖分别遵循其权利人的许可。

## 项目结构

```text
download-standards/                主技能，可直接安装
  SKILL.md                        工作流与判断规则
  agents/openai.yaml              中文显示及自动调用配置
  references/                    国内、国际、工程、获取与结果参考
  scripts/                       下载、文件检查、阅读页合成
  tests/                         临时夹具及本地HTTP测试
download-engineering-standards/   旧名称兼容入口
docs/                            安装、工作流程与验证说明
.github/workflows/               自动测试配置
```

## 测试与贡献

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r download-standards/tests/requirements.txt
python -m unittest discover -s download-standards/tests -v
```

已有24项辅助工具测试，使用临时文件和本地HTTP服务，不需要账号、不下载真实标准、不购买资料。测试不证明所有网站当前开放或任意标准已核验。[验证范围](docs/verification.md) · [贡献指南](CONTRIBUTING.md)。

欢迎补充可核实官方入口、修复获取/校验问题、完善版本处理。问题报告附脱敏错误和可公开链接，不附账号请求头或受限制标准全文。

[MIT License](LICENSE) · 维护者：[Aegean1218](https://github.com/Aegean1218)

## English overview

A Codex skill for finding, acquiring, and verifying standards across domains and jurisdictions. It prioritizes complete original documents, checks editions and amendments, preserves provenance and watermark information, and explains alternatives when acquisition fails. It does not bypass access restrictions or promise free downloads. Install `download-standards`; optionally install `download-engineering-standards` beside it for legacy invocation. Reports default to Chinese. See [installation](docs/installation.md) and [workflow](docs/workflow.md).
