# 工作流程与工具

技能负责实时发现来源、识别标准体系、核验正式状态、操作正常网页和最终判断。辅助脚本只处理已发现的URL、技术检查和本地单页合成，不自动全网搜索。

主入口：[SKILL.md](../download-standards/SKILL.md)。相关参考：[来源路由](../download-standards/references/sources.md)、[国内](../download-standards/references/sources-china.md)、[国际/国外](../download-standards/references/sources-international.md)、[工程专项](../download-standards/references/sources-engineering.md)。

## 已发现的文件URL

在仓库根目录、已准备依赖的环境：

```sh
python download-standards/scripts/download.py --url '实际已发现的文件URL' --output 'outputs/标准.pdf' --referer '来源页面URL' --expected-standard '完整标准号' --report outputs/download.json
python download-standards/scripts/inspect_document.py outputs/标准.pdf --expected-standard '完整标准号' --report outputs/inspection.json
```

地址和编号用实际值替换，不能猜受保护接口。默认有限重试，401/402/403/404不机械重复；跨来源跳转不转发认证头，HTTPS降级被拒绝，现有输出不覆盖。

成功状态仍为 `downloaded_pending_review`。Codex继续核对正式版本、文档头、目录/正文、全页连续性、附件、末页和水印后，才能给“已下载并核验”。扫描件、旧DOC及解析异常须额外检查。

`--expected-pages`只用可信来源已确认页数，不能填回下载文件自身页数。辅助脚本只支持PDF/Word；TXT/HTML/XML应使用适合的保存和核验方式，不改扩展名冒充PDF。

## 批量与阅读页

批量清单为JSON数组，每项有 `url`、`output`，可附 `referer`、`expected_standard`、`expected_pages`：

```sh
python download-standards/scripts/download.py --batch work/downloads.json --report outputs/downloads.json
```

任一失败退出码1，但成功项保留。额外请求头只用用户明确提供/授权的私有 `--headers-file`，仅用于单URL，不提交Git、不写进报告。

只有完整、有权访问且允许保存的已观测单页，才能合成阅读副本。清单有 `source_url`、已知 `expected_pages` 和从1连续编号的本地 `pages`：

```sh
python download-standards/scripts/assemble_pages.py --manifest work/pages.json --output outputs/阅读副本.pdf --report outputs/reader-copy.json
```

缺页、重号、未知总页数不能生成“完整副本”；另视觉检查内容顺序、重复和截断，始终标阅读副本，保留原页水印。

详细接口、清单字段和状态见[工具与结果](../download-standards/references/tools-and-results.md)，权限/阅读器分支见[获取参考](../download-standards/references/acquisition.md)。国际标准无统一实施日期时如实记录，企业文件无台账时不凭修改时间认定最新版。
