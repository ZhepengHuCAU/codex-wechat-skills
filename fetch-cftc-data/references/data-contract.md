# 官方来源与字段

| 口径 | Socrata 数据集 | `futonly_or_combined` |
|---|---|---|
| Disaggregated Futures Only | `72hh-3qpy` | `FutOnly` |
| Disaggregated Futures and Options Combined | `kh3c-gbw2` | `Combined` |

API：`https://publicreporting.cftc.gov/resource/<dataset-id>.json`。无需账号或 API 密钥。使用 SoQL `$select`、`$where`、`$order`、`$limit`、`$offset` 分页，下载前后核对 `count(*)`；行数变化时停止，稍后用新输出目录重试。行数不变不能排除历史值修订，因此保留原始响应及哈希。

代码是六位字符串。内置别名 `soybeans=005602`、`corn=002602`；其他品种先在 [CFTC门户](https://publicreporting.cftc.gov/stories/s/r4w3-av2u)核实代码和交易所，再用 `--codes`。不同交易所、迷你合约等代码不能擅自合并。

| 官方字段 | 含义 |
|---|---|
| `report_date_as_yyyy_mm_dd` | 持仓快照日期，不是发布日期 |
| `cftc_contract_market_code` | 合约市场代码，保留前导零 |
| `market_and_exchange_names` | 市场和交易所名称 |
| `m_money_positions_long_all` | Managed Money 多头 |
| `m_money_positions_short_all` | Managed Money 空头 |
| `open_interest_all` | 总未平仓量 |
| `futonly_or_combined` | 仅期货/期货加期权标识 |

净头寸 = 多头 − 空头，可为负。净头寸/OI = 净头寸 ÷ 总未平仓量 × 100%，不是历史分位数、COT 指数或基金多头占比。数量单位为合约手数，绘图换成万手时除以10000。Combined 期权转换为期货等值，脚本允许非负小数，不提前取整。不把 spreading 再加到净头寸。

Legacy Noncommercial、Disaggregated Managed Money、TFF Leveraged Funds 是不同分类，不拼接、不互相改名。

# 历史和发布日期

[CFTC历史数据说明](https://www.cftc.gov/PressRoom/PressReleases/5737-09)明确：Disaggregated 历史追溯到 **2006年6月13日**，早期使用回溯分类（backcasting）。其他新加入市场可能更晚。2006—2026涉及21个年份，不等于21整年，更不等于30年。

[官方用户指南](https://publicreporting.cftc.gov/stories/s/COT-Help/p2fg-u73y/)说明一般每周五发布此前周二收盘持仓；节假日、停摆或其他延误可能改变安排。脚本保存实际日期；距查询结束日超过14天、相邻记录超过10天会提示核查，不把提示直接解释成漏下载。

# 同期纪录的定义

使用最新一期或 `--compare-date` 指定且存在的一期。排名排除比较日之后的观察值；这不构成历史实时版本数据库，上游后来修订过的旧值仍可能在其中。

- `iso-week`：相同 ISO 周、按 ISO **周年**分组，避免一月初/十二月底错用日历年。同一周年同周有多期则报错，需要人工决定规则。
- `nearest-date`：每个日历年以比较日月日为中心取±3日最近一期；二月29日在非闰年映射二月28日。同距离取较早日期。
- 排名 = 1 + 严格大于当前净头寸的观察数；并列第一与严格创新高分开输出。存在此前样本且当前值严格超过此前最大值，才是创纪录。
- 输出逐年样本、缺失年份、样本数量、样本起止和原始序列跨度。缺年时只能写“已取得的N年样本中最高”。
- 全样本最大值与同周最大值分开；最大值只对下载区间有效。
- 写“有可比数据以来”前，确认请求覆盖官方可得起点、各年同期齐全；不能默认已验证 `--start` 之前的年份。

# 导出质量

唯一键：报告口径 + 市场代码 + 日期。字段缺失、混合口径、重复键、非数值、负多头/空头/OI会停止。API返回请求范围外记录也停止。OI为零时比例留空；基金单边持仓超过总OI时提示。市场最新日期不齐、请求市场无数据、明显日期断档需说明。

工具不获取价格、库存或收益；持仓纪录不能独立证明未来价格涨跌或因果关系。
