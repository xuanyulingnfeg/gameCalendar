# scripts/ — 活动日历维护脚本

本目录存放由 WorkBuddy（Claw 工作区）维护、用于自动更新 `config/activities.json` 的脚本。
**脚本本身不包含任何账号 / 推送凭证**，凭证全部在本地解析（见 `_daily_notify.py` 内的凭证解析链）。

| 脚本 | 作用 |
| ---- | ---- |
| `refresh_game_cache.py` | 抓取游戏公告 → 解析活动 → 刷新本地缓存；**检测到版本切换时自动把新活动写入本仓库 `config/activities.json`，并 commit + push gh-pages** |
| `_daily_notify.py` | 每日 10:30 微信推送「未完成活动总览」；也可手动 `--text "…"` 直推指定文本 |
| `_tj_cal_ocr.py` | 《异环》塔吉多「活动日历长图」下载 + 分块 OCR（仅用于人工核对排期，不影响流水线） |

## 运行方式

脚本的运行数据（缓存、完成状态、推送哨兵）**不在本仓库**，默认位于 Claw 工作区的 `game-activity-cache/`。
因此从本目录运行时必须用环境变量指回：

```bash
export GAC_HOME="C:\\Users\\Administrator\\WorkBuddy\\Claw"   # 缓存/哨兵所在目录
# 可选：
export GAC_CACHE_DIR="…"            # 缓存目录（默认 $GAC_HOME/game-activity-cache）
export GAC_CAL_PROJECT="…"          # 本仓库路径（脚本在 scripts/ 下时自动取上级目录，无需设置）
```

常用命令：

```bash
python refresh_game_cache.py                    # 刷新全部在玩游戏的缓存（未过期则纯本地重算，不联网）
python refresh_game_cache.py --no-network       # 强制纯本地重算（不联网）
python refresh_game_cache.py --force-network    # 忽略缓存有效期，强制联网抓取（仅目标游戏）
python refresh_game_cache.py --dump-text        # 导出公告纯文本（排查解析问题）
python refresh_game_cache.py --game 异环 --fetch-banners --apply   # 抓 red（限时角色）条目并写回日历
python _daily_notify.py                          # 推送「未完成活动总览」到微信
```

## 依赖

- Python 3.13（WorkBuddy 托管解释器 `~/.workbuddy/binaries/python/versions/3.13.12/python.exe`）
- 可选：`pypinyin`（角色名 → charIcons 拼音文件名）、`rapidocr-onnxruntime` + `pillow` + `numpy`（公告长图 OCR）
  缺少时脚本会降级（打印 warn）而不报错中断。

## 约定

- 活动条目顺序：`red`（限时角色）→ `orange`（≥25 天长活动）→ `gray`，同类按开始时间升序。
- 时间格式 `YYYY-MM-DD HH`，结束时间按 **59 分进位**到下一整点（如 `05:59` → `06`）。
- `charIcons` 路径 = `./{游戏key}/{角色名全量拼音小写}.png`，**图标文件由人工补齐**（脚本只写路径，不抓图）。
- 排除同步的活动：名称含「回归」「签到」者；《异环》另排除弧盘研募 / 全新剧情 / 联动盲盒 / 网页活动 / 「XX开市预演」角色试用。

> 本目录是脚本的**发布副本**，源头在 Claw 工作区；由 WorkBuddy 侧修改后同步过来。
