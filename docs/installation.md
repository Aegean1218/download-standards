# 安装、更新与运行环境

主技能为仓库的 `download-standards/`；旧名称兼容入口为 `download-engineering-standards/`。可按README用Codex内置skill-installer安装，或手动复制目录。

有内置安装脚本时，从其实际位置执行：

```sh
python3 <skill-installer目录>/scripts/install-skill-from-github.py --repo Aegean1218/download-standards --path download-standards download-engineering-standards
```

替换安装器目录为本机实际路径。默认 `$CODEX_HOME/skills/`，未配置时通常为 `~/.codex/skills/`。不把整个Git仓库当作一个技能目录。主技能可独立安装，旧名称需要两个目录同级；安装后下一轮或新会话调用 `$download-standards`。

## 辅助脚本依赖

Python 3.10+。在使用技能的工作区准备环境，不修改系统Python：

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r /实际技能路径/download-standards/scripts/requirements.txt
```

Windows可使用 `.venv\Scripts\Activate.ps1`，或直接调用该虚拟环境的Python。依赖为requests、PyMuPDF、python-docx；测试另需Pillow。有平台提供文档运行环境时先检查现有依赖。

技能文件安装本身不要求预先运行辅助脚本。官方HTML/TXT/XML和正常浏览器导出可采用适合的其他工具。

## 更新与卸载

更新前备份现有两个技能目录并保留个人改动；拉取仓库后以新目录替换，下载文件不存入技能目录。内置安装器拒绝覆盖，先备份并移出旧目录再安装。

卸载时移除相应技能目录。用户工作区标准文件、报告和虚拟环境独立保留。

## 常见问题

- 未发现技能：确认目录和SKILL.md位置，在下一轮或新会话显式调用。
- 缺依赖：确认使用工作区虚拟环境的Python。
- 旧名称缺主技能：安装两个同级目录，或直接调用主技能。
- 下载失败/只有预览：安装成功不表示站点开放全文，需记录实际权限、HTTP和页面范围，继续其他来源。
