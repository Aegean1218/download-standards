# 工具接口与结果记录

## 运行条件

Python 3.10+。需要 `requests`、`PyMuPDF`、`python-docx`，依赖见 `scripts/requirements.txt`。先检查当前/平台提供的文档运行环境；缺失时只在工作区虚拟环境安装，不修改系统 Python。脚本路径以实际 skill 根目录为准，以下 `<skill>`、`<output>` 是操作示例占位符，不是待实现内容。

## 下载与检查

```sh
python3 <skill>/scripts/download.py --url '已发现的实际文件URL' --output '<output>/标准号_名称.pdf' --referer '来源页面URL' --expected-standard 'SJG 223-2026' --report '<output>/download.json'
python3 <skill>/scripts/inspect_document.py '<output>/标准号_名称.pdf' --expected-standard 'SJG 223-2026' --report '<output>/inspection.json'
```

`--expected-pages` 仅在从可信来源确定总页数后使用；不要把下载出来的页数自己填回作为完整性验证。下载报告记录重定向、请求次数、字节数、SHA-256 和文件检查。`ok=true` 仍是待核验；HTTP/结构检查永远不自动发出“已核验”。出现标准编号不符、草稿/预览、页数不符等警告时必须解决或保持待核验。

文件检查扫描 PDF 全部页，报告解析修复、低文本页和封面身份线索；不给出整本标准文本。原生 DOCX 页数为 `null`，实际分页在 Word/兼容阅读器检查。旧 `.doc` 的 OLE 文件仅标“未核验旧格式”，需原生应用确认它是有效 Word、身份、内容与分页；不要仅凭 OLE 文件头认定已校验。

`--expected-standard` 支持完整标识字符串，例如 `ISO/IEC 27001:2022`、`ASTM A36/A36M-19`、`RFC 8259`。检查是封面文本匹配线索，不能代替版次、语言、国家采纳版本和修订附件核验。若封面拆字、扫描、跨页或排版导致未匹配，视觉确认后解释原因，不修改原文件去迎合匹配。

HTML/TXT/XML/ZIP 等官方原生文件不适用此 PDF/Word 下载检查脚本；用普通 HTTP/浏览器保存，并按 [国际与开放规范](sources-international.md) 核对结构和内容。原生文件无固定分页时页数填 `null`，不捏造 PDF 页数。ZIP 逐个核对目标成员；数据表、电子附件缺失时必须记录。

批量下载输入 JSON 数组（输出路径最好绝对路径）：

```json
[
  {"url":"https://example.org/observed.pdf","output":"/workspace/outputs/标准A.pdf","expected_standard":"SJG 223-2026"},
  {"url":"https://example.org/observed.docx","output":"/workspace/outputs/标准B.docx","referer":"https://example.org/notice"}
]
```

```sh
python3 <skill>/scripts/download.py --batch '<work>/downloads.json' --report '<output>/downloads.json'
```

批量结果每项独立保存；任一失败则退出码 1，但成功项仍保留。检索阶段由 agent 依据来源路由完成，下载脚本不声称自动完成全网检索。额外请求头使用私有 `--headers-file`，只允许单 URL，不与跨站批量混用。

阅读页清单包含 `source_url`、已知 `expected_pages`、可选 `expected_standard` 和 `pages` 数组；每项 `number` 从 1 到总页数，`path` 是已保存单页 PDF 或图片。相对路径以清单所在目录为基准。

```sh
python3 <skill>/scripts/assemble_pages.py --manifest '<work>/pages.json' --output '<output>/标准号_阅读副本.pdf' --report '<output>/reader-copy.json'
```

总页数或任一页未知/缺失则拒绝合成。视觉确认内容对应仍由 agent 完成。`artifact_kind=reader_copy` 永不改称官方原文件。

## 最终记录

为每项在 `results.json` 中记录以下字段；缺失值用 `null` 或“未确认”，不凭空补齐。报告默认用中文，机器枚举值在此映射。

| 字段 | 内容 |
|---|---|
| request | 用户原始目标、指定年份/地区/历史日期 |
| identity | 完整编号/文件号、正式名称、发布机构、国家/地区、标准类型、语言、分册、版本/修订号；采标及译本关系按需记录 |
| version | 发布/实施或生效日期、核验日期、官方状态原文及中文说明、现行/未实施/被代替/废止/待核验、替代关系；无统一实施日时填不适用/未公布，不拿其他日期代替 |
| changes | 修改单、勘误、补遗、局部修订、强条废止、Amendment/Corrigendum/Addenda、开放规范更新关系及证据；下载的配套文件；官方整合版所含修订 |
| status | 下表结果状态 |
| artifact_kind | 官方原文件、公开副本、扫描件、阅读页副本（可组合） |
| file | 本地路径、真实格式、字节数、页数、SHA-256；无文件则 null |
| evidence | 官方版本证据链接；文件来源及最终 URL；完整性依据和未解决问题 |
| quality | 水印已确认/抽检/未知、图表公式清晰度、条文说明/电子附件/数据表是否包含或不适用；翻译和生成方式 |
| attempts | 所试来源、方法、HTTP/权限/工具错误及结果；隐藏令牌和账号信息 |
| alternatives | 实际可访问的阅读/购买/数据库/图书馆链接，可见范围和必要条件 |

| 最终状态 | 条件 |
|---|---|
| 已下载并核验 `downloaded_verified` | 文件可打开；身份及版本获官方证据支持；正文/目录/全页连续性/附录/末页已核对；异常已解决 |
| 已下载待核验 `downloaded_pending_review` | 取得可用文件，但身份、版本、完整性或损坏修复等还有未确认项 |
| 仅可在线阅读 `online_only` | 实测可读而未取得可保存全文；说明全文/预览及可见范围 |
| 需登录或购买 `access_required` | 目标获取入口需要尚未具备的权限，且没有取得可靠公开全文 |
| 未找到 `not_found` | 所试路线无可靠目标，或没有可验证的可用入口 |
| 待澄清 `needs_clarification` | 缺发布主体、地区、版次等必要信息，无法唯一确定目标；其他明确项继续 |
| 未执行 `not_attempted` | 仅候选、用户尚未选择、模拟测试或尚未检索；说明原因，不冒充未找到或在线阅读 |

`invalid_file`、`download_failed`、`assembly_failed` 是辅助工具诊断，不当成成功下载。水印和条文说明是独立质量字段：完整文件有水印仍可核验；未确认水印不能声称无水印。版本未获实时核验不能声称最新。最新版本取不到、只有旧版时，旧版另列为附带参考，不能用旧版给最新版本目标报成功。

无目录的短规范、无分页的网页规范或无实施日期的国际规范，按其真实结构记录“不适用”及替代完整性证据，不虚构工程式结构。文件结构符合其出版说明、所有要求的章节/附件齐全才可报全文核验。

最终聊天给简短逐项结果、文件链接、必要版本/水印说明和失败替代渠道；另附详细核验记录。只列已取得的本地文件，不把购买页或搜索结果写成下载链接。

## 本地自检

测试依赖另见 `tests/requirements.txt`（增加 Pillow，仅测试图像页夹具需要）。

```sh
python3 -m unittest discover -s <skill>/tests -v
```

测试使用临时文件及本机 HTTP 服务，不购买资料，不写入外部账号。
