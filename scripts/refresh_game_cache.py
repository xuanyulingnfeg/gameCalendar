#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏活动进度缓存定时刷新脚本
- 始终执行「本地重算」：依据各活动已缓存的 start/end 与当前时间，重算 status，
  并按 SKILL.md 的固定活动轮换规则重算当期窗口与 fixed_key。
- 尽力执行「联网刷新」：重新抓取公告、解析活动；只有严格校验通过才覆盖缓存，
  否则回退到本地重算结果（绝不破坏已有缓存）。
- 不在本脚本内执行 git 推送 / 日历项目同步；若检测到版本切换，仅打印 ALERT 提示用户人工确认同步。
"""
import json
import os
import re
import sys
import subprocess
from datetime import datetime, timezone, timedelta

try:
    from pypinyin import lazy_pinyin, load_phrases_dict
except ImportError:
    lazy_pinyin = None  # charIcons 拼音生成依赖；缺失时回退中文名文件名
    load_phrases_dict = None

TZ = timezone(timedelta(hours=8))  # 中国标准时间 UTC+8
HERE = os.path.dirname(os.path.abspath(__file__))
# 运行数据目录：默认与脚本同目录；脚本被放到别处（如 gameCalendar 仓库 scripts/）时，
# 用环境变量 GAC_HOME 指回 Claw 工作区即可，无需改代码。
HOME = os.environ.get("GAC_HOME") or HERE
CACHE_DIR = os.environ.get("GAC_CACHE_DIR") or os.path.join(HOME, "game-activity-cache")

# ---- 固定活动轮换规则（来源 SKILL.md）----
# 结构: 游戏 -> [(名称, 周期天数, 参考起始日, key前缀, 是否随版本)]
FIXED_SPEC = {
    "绝区零": [
        ("式舆防卫战", 14, "2026-07-24 04:00", "绝区零_式舆防卫战_", False),
        ("危局强袭", 14, "2026-07-31 04:00", "绝区零_危局强袭_", False),
    ],
    "鸣潮": [
        ("深境再临", 28, "2026-07-20 04:00", "鸣潮_深境再临_", False),
        ("冥歌海虚", 28, "2026-08-03 04:00", "鸣潮_冥歌海虚_", False),
        ("终焉矩阵", 0, "", "鸣潮_终焉矩阵_", True),  # 随版本
    ],
    "异环": [
        # 轨外之境·特别路线：每 14 天一轮（官方 2026-06-26 起固定 14 天轮换）
        # 当期：勺照环线 2026-10-02 05:00 ~ 2026-10-16 04:59
        ("轨外之境", 14, "2026-10-02 05:00", "异环_轨外之境_", False),
    ],
}

DT_FMTS = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H", "%Y/%m/%d %H:%M", "%Y/%m/%d %H")

# 中文年月日格式（2026年8月20日04:00 / 2026年8月20日04：00）→ 数字格式
_CN_DT_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(\d{1,2})[:：](\d{2})")


def _normalize_dt_text(s):
    """把文本中的中文年月日时间归一化为 YYYY-MM-DD HH:MM。"""
    return _CN_DT_RE.sub(
        lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} "
                  f"{int(m.group(4)):02d}:{m.group(5)}",
        s or "")


# 中文「M月D日」无年份格式（《异环》公告用，如「9月28日05:00-11月5日05:59」）
_CN_MD_RE = re.compile(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日(?:\s*(\d{1,2})[:：](\d{2}))?")


def _normalize_md_dates(s, base_year=None, base_month=None):
    """把无年份的「M月D日」补成 YYYY-MM-DD（可带 HH:MM），年份按版本起始时间推断。
    月份比基准月小 6 个月以上视为跨年（+1 年）。"""
    if not s:
        return s or ""
    if base_year is None:
        n = now()
        base_year, base_month = n.year, n.month
    if base_month is None:
        base_month = 1

    def _rep(m):
        mo, d = int(m.group(1)), int(m.group(2))
        hh, mi = m.group(3), m.group(4)
        y = base_year + 1 if mo < base_month - 6 else base_year
        if hh is None:
            return f"{y}-{mo:02d}-{d:02d}"
        return f"{y}-{mo:02d}-{d:02d} {int(hh):02d}:{mi}"

    return _CN_MD_RE.sub(_rep, s)


def parse_dt(s):
    s = _normalize_dt_text((s or "").strip())
    for fmt in DT_FMTS:
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=TZ)
        except ValueError:
            pass
    return None


def now():
    return datetime.now(TZ)


def recompute_status(start, end, t):
    if start and t < start:
        return "upcoming"
    if end and t >= end:
        return "ended"
    return "active"


def version_num_from_title(title):
    m = re.search(r"(\d+\.\d+)\s*版本", title or "")
    return m.group(1) if m else "?"


def recompute_fixed(game, name, version_start, version_end, version_num, t):
    """返回 (start_str, end_str, fixed_key, status) 或 None（非固定活动）。"""
    for spec in FIXED_SPEC.get(game, []):
        sname, cycle, ref_s, prefix, follow_version = spec
        if name != sname:
            continue
        if follow_version:
            s = parse_dt(version_start)
            e = parse_dt(version_end)
            if s:
                # 终焉矩阵阶段开启：版本更新后第 7 天 04:00（官方公告规则，2026-08-22 确认）
                s = (s + timedelta(days=7)).replace(hour=4, minute=0)
            # key 用当期开始时间 YYYYMMDD（2026-09-09 起，替换版本号）
            key = f"{prefix}{s.strftime('%Y%m%d')}" if s else f"{prefix}{version_num}"
            status = "active" if (s and e and s <= t < e) else ("upcoming" if (s and t < s) else "ended")
            return (_fmt(s), _fmt(e), key, status)
        ref = parse_dt(ref_s)
        if not ref:
            return None
        if t < ref:
            idx = -1
        else:
            idx = (t - ref).days // cycle
        start = ref + timedelta(days=cycle * idx)
        end = start + timedelta(days=cycle)
        # key 用当期开始时间 YYYYMMDD（2026-09-09 起，替换期数 idx）
        return (_fmt(start), _fmt(end), f"{prefix}{start.strftime('%Y%m%d')}", "active")
    return None


def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def _version_num(version_start):
    m = re.search(r"(\d+\.\d+)", version_start or "")
    return m.group(1) if m else "?"


# ---------------- 本地重算（可靠核心）----------------
def local_recompute(cache, t):
    game = cache.get("game")
    vstart = cache.get("version_start")
    vend = cache.get("version_end")
    vnum = version_num_from_title(cache.get("title"))
    out = []
    for act in cache.get("activities", []):
        a = dict(act)
        s = parse_dt(a.get("start"))
        e = parse_dt(a.get("end"))
        if a.get("type") == "fixed":
            fr = recompute_fixed(game, a.get("name"), vstart, vend, vnum, t)
            if fr:
                a["start"], a["end"], a["fixed_key"], a["status"] = fr
            else:
                a["status"] = recompute_status(s, e, t)
        else:
            a["status"] = recompute_status(s, e, t)
        out.append(a)
    # 活动内容按开始时间升序排序（规则：修改活动内容时需按开始时间排序）
    return sort_activities(out)


# ---------------- 联网刷新（尽力 + 严格校验）----------------
def _http_get(url, headers=None, data=None, timeout=20):
    import urllib.request
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def fetch_zzz_post():
    """返回 (post_id, title, html) 或 None。
    列表接口带 offset={post_id} 向前翻页；官方账号发帖频繁，故翻页最多 5 页再判定未找到。"""
    try:
        import urllib.parse
        h = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.miyoushe.com/"}
        post_id = None
        title = None
        offset = None
        for _ in range(5):
            url = "https://bbs-api.miyoushe.com/painter/wapi/userPostList?size=20&uid=152039148"
            if offset:
                url += f"&offset={offset}"
            items = json.loads(_http_get(url, h)).get("data", {}).get("list", [])
            if not items:
                break
            for it in items:
                sub = it.get("post", {}).get("subject", "")
                if "版本" in sub and "更新公告" in sub:
                    post_id = it.get("post", {}).get("post_id")
                    title = sub
                    break
            if post_id:
                break
            offset = items[-1].get("post", {}).get("post_id")
        if not post_id:
            return None
        url2 = f"https://bbs-api.miyoushe.com/post/wapi/getPostFull?post_id={post_id}"
        full = json.loads(_http_get(url2, h))
        html = full.get("data", {}).get("post", {}).get("post", {}).get("content", "")
        return post_id, title, html
    except Exception as ex:
        print(f"[warn] 绝区零联网失败: {ex}")
        return None


# 库洛社区接口需要完整设备头，否则 getPostDetail 返回 code=102 服务器外部错误
_MC_HEADERS = {
    "osversion": "Android",
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "okhttp/3.11.0",
    "devCode": "073A9EFAC18FC50616DD15808DAE719DBCB904B7",
    "distinct_id": "96b1567b-b5e6-422f-a1dd-7cb1e58c5db7",
    "countrycode": "CN",
    "source": "android",
    "lang": "zh-Hans",
    "version": "2.2.0",
    "versionCode": "2200",
    "model": "23127PN0CC",
}


def fetch_mc_post():
    """返回 (post_id, title, html) 或 None。"""
    try:
        import urllib.parse
        h = _MC_HEADERS
        post_id = None
        title = None
        for page in range(1, 10):
            body = urllib.parse.urlencode({"searchType": "1", "type": "2",
                                           "otherUserId": "10012001",
                                           "pageIndex": str(page), "pageSize": "10"}).encode()
            lst = json.loads(_http_get("https://api.kurobbs.com/forum/getMinePost", h, body))
            for p in lst.get("data", {}).get("postList", []):
                t = p.get("postTitle") or ""
                if "版本" in t and ("内容说明" in t or "更新" in t):
                    post_id = p.get("postId")
                    title = t
                    break
            if post_id:
                break
        if not post_id:
            return None
        body = urllib.parse.urlencode({"postId": str(post_id),
                                       "isOnlyPublisher": "0", "showOrderType": "2"}).encode()
        det = json.loads(_http_get("https://api.kurobbs.com/forum/getPostDetail", h, body))
        pd = det.get("data", {}).get("postDetail", {})
        html = pd.get("postH5Content") or pd.get("postContent") or ""
        return post_id, title, html
    except Exception as ex:
        print(f"[warn] 鸣潮联网失败: {ex}")
        return None


# 《异环》塔吉多社区官方账号 uid
TJ_UID = "10100006"


def fetch_tj_post():
    """《异环》塔吉多社区更新公告。返回 (post_id, title, text) 或 None。

    - 列表接口 `GET /bbs/wapi/getUserPostList?uid={uid}&version={cursor}`，**游标分页**：
      把上一响应的 `data.version` 原样回传即取更旧一批（`version=0` 为最新），无 page/offset。
    - 正文在 `structuredContent`（JSON 字符串，块数组）中，按序拼接各块 `txt` 即得全文；
      `content` 字段只有 300 字预览，不可用。
    - 标题形如 `《异环》1.4版本「祷歌为谁而诵」更新公告`（1.2/1.1 无《异环》前缀）。
    """
    try:
        h = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.tajiduo.com/"}
        cursor, post = 0, None
        for _ in range(8):
            url = ("https://bbs-api.tajiduo.com/bbs/wapi/getUserPostList"
                   f"?uid={TJ_UID}&version={cursor}")
            data = json.loads(_http_get(url, h)).get("data", {})
            for it in data.get("posts", []):
                sub = it.get("subject", "") or ""
                if "版本" in sub and "更新公告" in sub:
                    post = it
                    break
            if post or not data.get("hasMore"):
                break
            cursor = data.get("version") or 0
        if not post:
            return None
        blocks = json.loads(post.get("structuredContent") or "[]")
        txt = "\n".join(str(b.get("txt")) for b in blocks
                        if isinstance(b, dict) and b.get("txt") is not None)
        return post.get("postId"), post.get("subject", ""), txt
    except Exception as ex:
        print(f"[warn] 异环联网失败: {ex}")
        return None


# 各游戏公告抓取器（network_refresh / --parse-only / --dump-text 统一分派）
FETCHERS = {
    "绝区零": fetch_zzz_post,
    "鸣潮": fetch_mc_post,
    "异环": fetch_tj_post,
}


_DATE_RE = re.compile(r"(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})")
_RANGE_RE = re.compile(r"(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})\s*(?:[-~至~—]|～)\s*(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})")
# 单侧时间：「3.6版本更新后 ~ 2026-09-29 03:59」这类，start 用版本开始时间补
_RANGE2_RE = re.compile(r"(?:\d+\.\d+\s*版本更新后|版本更新后)\s*(?:[-~至~—]|～)\s*(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})")
# 维护时间：「更新维护时间：\n2026-08-20 04:00 ~ 2026-08-20 11:00」（匹配前先剥 HTML 标签）
_MAINT_RE = re.compile(r"维护时间[^\d]{0,20}(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})\s*(?:[-~至~—]|～)\s*(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})")
# 维护时间同日省略日期：「更新维护时间：2026年9月24日06:00 - 11:00」（《异环》用）→ 取结束时刻
_MAINT2_RE = re.compile(r"维护时间[^\d]{0,20}(\d{4})[-/](\d{2})[-/](\d{2})\s+(\d{1,2})[:：](\d{2})\s*(?:[-~至~—]|～)\s*(\d{1,2})[:：](\d{2})")
# 新版公告：「【更新开始时间】2026/09/09 06:00」+「预计5个小时完成」→ 维护结束=开服
_UPD_START_RE = re.compile(r"(?:更新开始时间|更新维护时间|维护开始时间)[^\d]{0,20}(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})")
_UPD_DUR_RE = re.compile(r"预计\s*(\d+)\s*个?\s*(小时|分钟)")
# 版本结束时间明文：「3.2版本结束时间为 2026/10/21 06:00」/「该版本共持续42天」
_VEND_RE = re.compile(r"版本结束时间[^\d]{0,20}(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})")
_VDAYS_RE = re.compile(r"该版本共持续\s*(\d+)\s*天")
# 相对区间：「3.2版本更新后 ~ 3.2版本结束」→ 起止用版本起止时间补齐
_RANGE3_RE = re.compile(r"版本更新后\s*(?:[-~至~—]|～)\s*(?:\d+\.\d+\s*)?版本结束")


# 元信息/描述行前缀，不应被当作活动名
_META_PREFIX = ("活动时间", "参与条件", "解锁条件", "开放条件", "注：", "※",
                "活动期间", "活动期限内", "领取时间", "补偿", "更新时间", "活动说明",
                "开放时间", "开启时间", "玩法说明", "棋盘说明", "研募说明")
# 独立成行的项目符号（《异环》公告的「●」单独一行）
_BULLETS = ("•", "●", "·", "◆", "■")

# ---- 活动内容排除规则（2026-09-09 用户确认）----
# 1) 登录/签到类活动不计入活动内容（名称或「名称行~活动时间行」之间的描述命中即剔除）
ACT_EXCLUDE_KW = ("累计登录", "累计签到", "七日签到", "登录签到", "签到")
# 2) 指定游戏按名称额外排除的活动（绝区零：潜能预演 系列）
ACT_EXCLUDE_NAME_KW = {
    "绝区零": ("潜能预演",),
}


def is_excluded_activity(name, ctx="", game=""):
    """判断活动是否应从活动内容中剔除；返回 (是否剔除, 命中原因)。"""
    text = f"{name}\n{ctx}"
    for kw in ACT_EXCLUDE_NAME_KW.get(game, ()):
        if kw in name:
            return True, f"名称排除[{kw}]"
    for kw in ACT_EXCLUDE_KW:
        if kw in text:
            return True, f"登录/签到类[{kw}]"
    return False, ""


def _pick_activity_name_at(text, pos, max_back=8, plain_ok=False):
    """从匹配位置向前找活动名行，返回 (name, 该行起始下标)；找不到返回 ("", -1)。

    plain_ok=True（《异环》版式）时，遇到**非元信息、非项目符号的普通行**即认定为活动名，
    因为异环公告为「● / 名称行 / 活动时间： / 时间」四行式。
    """
    idx = 0
    prev = []
    for ln in text.split("\n"):
        # 只收集「在匹配位置之前**整行结束**」的行，避免把匹配所在的同一行当活动名
        # （《异环》的「9月24日版本更新后-11月5日05:59」归一化后匹配起点在行中间）
        if idx + len(ln) < pos:
            prev.append((idx, ln.strip()))
        idx += len(ln) + 1
    for i, ln in reversed(prev):
        if not ln:
            continue
        # 时间匹配位置切开后残留的「活动时间：」片段
        if re.match(r"^活动时间[:：]?$", ln):
            continue
        if ln.startswith(_META_PREFIX):
            continue
        if ln in _BULLETS:  # 独立成行的项目符号 → 跳过继续向前
            continue
        if ln.startswith("["):
            return ln, i
        if ln.startswith(_BULLETS):
            return re.sub(r"^[" + "".join(_BULLETS) + r"]\s*", "", ln), i
        if plain_ok:
            return ln, i
        max_back -= 1
        if max_back <= 0:
            break
    return "", -1


def _pick_activity_name(text, pos, max_back=8, plain_ok=False):
    """从匹配位置向前找活动名行。
    优先 [xxx]（鸣潮格式）与「• xxx」（绝区零 3.2+ 格式）名称行；
    跳过「活动时间：」等元信息行与描述行（这些行可能夹在名称与时间之间）。
    找不到名称行则返回空串，由调用方跳过该候选，避免写入「活动时间：」这类占位名。
    plain_ok=True 时把普通行也当作名称（《异环》版式）。"""
    return _pick_activity_name_at(text, pos, max_back, plain_ok)[0]


def parse_activities_from_html(html, version_start="", version_end="", game=""):
    """尽力从公告 HTML 提取 (name, start, end) 候选列表。
    返回 (cands, excluded)；excluded 为被规则剔除的 (name, 原因) 列表。
    剔除规则：登录/签到类活动、绝区零「潜能预演」系列。"""
    cands, excluded = [], []
    if not html:
        return cands, excluded
    text = _normalize_dt_text(html)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    plain_ok = (game == "异环")

    if game == "异环":
        # 《异环》公告：日期为「M月D日」无年份 → 按版本起始时间补年份
        _vs0 = parse_dt(version_start)
        if _vs0:
            text = _normalize_md_dates(text, _vs0.year, _vs0.month)
        else:
            text = _normalize_md_dates(text)
        # 活动集中在「六、全新活动」章节，只解析该段（避免把角色/弧盘的「开放时间」当活动）
        _m6 = re.search(r"六、\s*\n?\s*全新活动", text)
        if _m6:
            _rest = text[_m6.start():]
            _nxt = re.search(r"(?m)^\s*七、", _rest)
            text = _rest[:_nxt.start()] if _nxt else _rest

    def _add(name, name_pos, s, e, end_pos):
        """统一清洗 + 排除判定 + 收录。"""
        name = re.sub(r"^[\s\d.、)#]+", "", name)
        name = name[-40:]  # 截断过长
        if not name:
            return
        ctx = text[name_pos:end_pos] if name_pos >= 0 else text[max(0, end_pos - 200):end_pos]
        hit, why = is_excluded_activity(name, ctx, game)
        if hit:
            excluded.append((name, why))
            return
        if plain_ok:
            # 「「噗卡乐园游记」限时活动」→「「噗卡乐园游记」」（去掉尾缀「限时活动」）
            name = re.sub(r"」\s*限时活动$", "」", name)
        cands.append((name, _fmt(s), _fmt(e)))

    # 优先限定在【版本活动】区块内（到下一个【 区块标题前），无该区块则全文
    if "【版本活动】" in text:
        text = text.split("【版本活动】", 1)[1]
        nxt = text.find("【")
        if nxt >= 0:
            text = text[:nxt]
    for m in _RANGE_RE.finditer(text):
        s_raw, e_raw = m.group(1), m.group(2)
        s = parse_dt(s_raw.replace("/", "-"))
        e = parse_dt(e_raw.replace("/", "-"))
        if not (s and e):
            continue
        name, name_pos = _pick_activity_name_at(text, m.start(), plain_ok=plain_ok)
        _add(name, name_pos, s, e, m.end())
    # 单侧时间：版本更新后 ~ 日期，start 用版本开始时间
    vs = parse_dt(version_start)
    for m in _RANGE2_RE.finditer(text):
        e = parse_dt(m.group(1).replace("/", "-"))
        if not e or not vs:
            continue
        name, name_pos = _pick_activity_name_at(text, m.start(), plain_ok=plain_ok)
        _add(name, name_pos, vs, e, m.end())
    # 相对区间：「版本更新后 ~ X版本结束」→ start=版本开始，end=版本结束
    vs0, ve0 = parse_dt(version_start), parse_dt(version_end)
    if vs0 and ve0:
        for m in _RANGE3_RE.finditer(text):
            name, name_pos = _pick_activity_name_at(text, m.start(), plain_ok=plain_ok)
            _add(name, name_pos, vs0, ve0, m.end())
    return cands, excluded


def sort_activities(acts):
    """活动内容按开始时间升序排序：版本活动在前、固定活动在后，各自连续编号 seq。"""
    def _key(a):
        s = parse_dt(a.get("start"))
        e = parse_dt(a.get("end"))
        if s is None:
            s = datetime.max.replace(tzinfo=TZ)
        if e is None:
            e = s
        return (s, e, a.get("name", ""))

    ver = sorted([a for a in acts if a.get("type") != "fixed"], key=_key)
    fixed = sorted([a for a in acts if a.get("type") == "fixed"], key=_key)
    out, seq = [], 1
    for a in ver + fixed:
        a = dict(a)
        a["seq"] = seq
        out.append(a)
        seq += 1
    return out


def validate_parse(text, cands, n_excluded=0, version_start=""):
    """校验解析出的活动内容是否与公告结构相符；返回 (ok, reasons)。
    不通过时交由 AI 直接解读公告内容（打印 NEEDS_LLM_PARSE）。"""
    reasons = []
    total = len(cands) + n_excluded
    if len(cands) < 3:
        reasons.append(f"候选活动数不足({len(cands)})")
    bad = [n for n, _, _ in cands
           if (not n) or n.startswith(_META_PREFIX) or re.match(r"^活动时间[:：]?$", n)]
    if bad:
        reasons.append(f"存在占位名({bad[:2]})")
    names = [n for n, _, _ in cands]
    if names and len(set(names)) < len(names) * 0.6:
        reasons.append("活动名重复过多")
    # 与公告中「活动时间」条目数比对（解析条数 = 保留 + 已剔除）
    n_marks = len(re.findall(r"活动时间", text))
    if n_marks >= 3 and abs(total - n_marks) > max(2, int(n_marks * 0.34)):
        reasons.append(f"解析条目数({total})与公告「活动时间」条目数({n_marks})不符")
    for n, s, e in cands:
        ds, de = parse_dt(s), parse_dt(e)
        if not (ds and de):
            reasons.append(f"时间无法解析({n})")
            break
        if de <= ds:
            reasons.append(f"时间区间非法({n})")
            break
    vs = parse_dt(version_start)
    if vs:
        early = [n for n, s, _ in cands
                 if parse_dt(s) and parse_dt(s) < vs - timedelta(days=3)]
        if early:
            reasons.append(f"活动开始时间早于版本开始({early[:2]})")
    return (not reasons), reasons


def validate_network(game, old_cache, cands, new_title, new_vstart, new_vend, t):
    """校验联网解析结果；返回 (ok, reason, is_new_version)。"""
    if not cands or len(cands) < 3:
        return False, "候选活动数不足", False
    for _, s, e in cands:
        if not (parse_dt(s) and parse_dt(e)):
            return False, "存在非法时间", False
    # 版本是否切换：以公告标题变化为准（new_vstart/new_vend 已由调用方从正文推断）
    new_version = bool(new_title) and new_title != old_cache.get("title")
    if new_version:
        nv_end = parse_dt(new_vend)
        if not (nv_end and nv_end > t):
            return False, "新版本结束时间不在未来", True
        return True, "新版本", True
    # 同版本：要求与旧版本活动名称高重合（旧缓存中被规则剔除的活动不计入比对）
    old_names = {a.get("name") for a in old_cache.get("activities", [])
                 if a.get("type") == "version"
                 and not is_excluded_activity(a.get("name", ""), "", game)[0]}
    new_names = {n for n, _, _ in cands}
    if not old_names:
        return True, "旧缓存无版本活动", False
    # 旧缓存活动名全是解析失败占位符（如「活动时间：」）→ 视为无效缓存，允许覆盖修复
    if all(re.match(r"^活动时间[:：]?$", n or "") for n in old_names):
        return True, "旧缓存活动名为占位符，允许覆盖", False
    overlap = len(old_names & new_names) / len(old_names)
    if overlap < 0.7:
        return False, f"名称重合度过低({overlap:.0%})", False
    if not (0.6 <= len(cands) / max(1, len(old_names)) <= 1.5):
        return False, "活动数量偏差过大", False
    return True, "同版本校验通过", False


def infer_version_start(html, fallback=""):
    """从公告推断版本开始时间（开服时间）。
    优先「维护时间 A ~ B」取 B；其次「更新开始时间 + 预计N小时」推算。"""
    nhtml = re.sub(r"<[^>]+>", "", _normalize_dt_text(html))
    mm = _MAINT_RE.search(nhtml)
    if mm:
        dt = parse_dt(mm.group(2))
        if dt:
            return _fmt(dt)
    m2 = _MAINT2_RE.search(nhtml)
    if m2:
        y, mo, d, _h1, _m1, h2, mi2 = m2.groups()
        try:
            return _fmt(datetime(int(y), int(mo), int(d), int(h2), int(mi2), tzinfo=TZ))
        except ValueError:
            pass
    ms = _UPD_START_RE.search(nhtml)
    if ms:
        vs = parse_dt(ms.group(1).replace("/", "-"))
        md = _UPD_DUR_RE.search(nhtml)
        if vs and md:
            n = int(md.group(1))
            vs = vs + (timedelta(hours=n) if md.group(2) == "小时" else timedelta(minutes=n))
        if vs:
            return _fmt(vs)
    return fallback


def infer_version_end(html, version_start="", fallback=""):
    """从公告推断版本结束时间：明文 → 「该版本共持续N天」→ 取最晚活动结束时间。"""
    nhtml = re.sub(r"<[^>]+>", "", _normalize_dt_text(html))
    me = _VEND_RE.search(nhtml)
    if me:
        dt = parse_dt(me.group(1).replace("/", "-"))
        if dt:
            return _fmt(dt)
    mdays = _VDAYS_RE.search(nhtml)
    vs = parse_dt(version_start)
    if mdays and vs:
        return _fmt(vs + timedelta(days=int(mdays.group(1))))
    return fallback


def network_refresh(game, old_cache, t):
    """返回 (new_activities_or_None, alert_or_None)。"""
    fetcher = FETCHERS.get(game)
    if not fetcher:
        print(f"[warn] {game} 未配置公告抓取器，跳过联网刷新")
        return None, None
    res = fetcher()
    if not res:
        return None, None
    post_id, title, html = res
    new_vstart = infer_version_start(html, old_cache.get("version_start", ""))
    # 版本结束时间：优先公告明文 → 其次「该版本共持续N天」→ 最后取最晚活动结束
    new_vend = infer_version_end(html, new_vstart, "") or None
    cands, excluded = parse_activities_from_html(html, new_vstart,
                                                 new_vend or old_cache.get("version_end", ""),
                                                 game)
    if excluded:
        print(f"[info] {game} 按规则剔除 {len(excluded)} 项："
              + "、".join(f"{n}({w})" for n, w in excluded))
    if not new_vend:
        ends = [e for _, _, e in cands if parse_dt(e)]
        if ends:
            new_vend = _fmt(max(parse_dt(e) for e in ends))
        else:
            new_vend = old_cache.get("version_end")
    # 解析校验：与公告结构比对，不通过则交给 AI 人工解读（NEEDS_LLM_PARSE）
    plain = re.sub(r"<[^>]+>", "\n", _normalize_dt_text(html))
    plain = "\n".join(l.strip() for l in plain.split("\n") if l.strip())
    ok_parse, why = validate_parse(plain, cands, len(excluded), new_vstart)
    if not ok_parse:
        path = os.path.join(CACHE_DIR, f"_announcement_{game}.txt")
        try:
            open(path, "w", encoding="utf-8").write(plain)
        except Exception as ex:
            print(f"[warn] 公告导出失败: {ex}")
            path = "(导出失败)"
        print(f"[warn] {game} 公告解析校验未通过（{'；'.join(why)}），回退本地重算")
        print(f"NEEDS_LLM_PARSE: {game} 公告原文已导出到 {path}")
        print("  → 请阅读该文本自行解读活动内容，再用 "
              f"--apply-json <file> 回填（格式：{{\"game\":\"{game}\","
              "\"activities\":[{\"name\":\"\",\"start\":\"YYYY-MM-DD HH:MM\","
              "\"end\":\"YYYY-MM-DD HH:MM\"}]}}）")
        return None, None
    ok, reason, is_new = validate_network(game, old_cache, cands, title, new_vstart, new_vend, t)
    if not ok:
        print(f"[warn] {game} 联网解析未通过校验({reason})，回退本地重算")
        return None, None
    # 构建新 activities：保留 fixed 条目（本地重算），叠加联网版本活动（已按开始时间排序）
    fixed = [a for a in old_cache.get("activities", []) if a.get("type") == "fixed"]
    fixed = local_recompute({"game": game, "title": title or old_cache.get("title"),
                              "version_start": new_vstart,
                              "version_end": new_vend, "activities": fixed}, t)
    version_acts = []
    for name, s, e in cands:
        version_acts.append({
            "seq": 0, "name": name, "status": recompute_status(parse_dt(s), parse_dt(e), t),
            "type": "version", "fixed_key": "", "start": s, "end": e,
        })
    new_acts = sort_activities(version_acts + fixed)
    alert = None
    if is_new:
        alert = f"ALERT: {game} 检测到版本切换（{title}），已更新缓存但未同步游戏日历，请确认后手动同步。"
    return {"post_id": str(post_id), "title": title,
            "version_start": new_vstart, "version_end": new_vend,
            "activities": new_acts}, alert


# ---------------- 完成态（cross-game）----------------
def _completion_key(game, activity):
    """生成与 completed.json 字段一致的 key。"""
    if activity.get("type") == "fixed" and activity.get("fixed_key"):
        return activity["fixed_key"]
    return f"{game}_版本活动_{activity.get('seq', 0)}"


def _load_completed():
    path = os.path.join(CACHE_DIR, "completed.json")
    if not os.path.exists(path):
        return {}
    try:
        return json.load(open(path, encoding="utf-8")).get("completed", {})
    except Exception:
        return {}


def _cleanup_old_version_completed(game):
    """版本切换后清理该游戏旧版本的版本活动完成记录。
    版本活动 key 为 {game}_版本活动_{seq}，新版本 seq 从 1 重新编号，
    若不清除旧 key 会把新活动误判为已完成。"""
    path = os.path.join(CACHE_DIR, "completed.json")
    if not os.path.exists(path):
        return
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return
    comp = data.get("completed", {})
    prefix = f"{game}_版本活动_"
    rm = [k for k in comp if k.startswith(prefix)]
    if not rm:
        return
    for k in rm:
        del comp[k]
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[info] {game} 版本切换：清理旧版本活动完成记录 {len(rm)} 条（{'、'.join(rm)}）")


def _remap_completed_keys(game, old_acts, new_acts):
    """活动内容重排/剔除后，按活动名把 {game}_版本活动_{seq} 的完成记录迁移到新 seq。
    已被剔除（名称不再存在）的活动，其完成记录一并删除，避免误判。"""
    old_map = {a.get("name"): a.get("seq") for a in old_acts if a.get("type") != "fixed"}
    new_map = {a.get("name"): a.get("seq") for a in new_acts if a.get("type") != "fixed"}
    if not old_map or not new_map:
        return
    path = os.path.join(CACHE_DIR, "completed.json")
    if not os.path.exists(path):
        return
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return
    comp = data.get("completed", {})
    prefix = f"{game}_版本活动_"
    moves, drops = {}, []
    for k in list(comp):
        if not k.startswith(prefix):
            continue
        name = next((n for n, s in old_map.items() if str(s) == k[len(prefix):]), None)
        if name is None:
            continue
        if name not in new_map:
            drops.append((k, name))
        elif str(new_map[name]) != k[len(prefix):]:
            moves[k] = f"{prefix}{new_map[name]}"
    if not moves and not drops:
        return
    for k in drops:
        comp.pop(k[0], None)
    for old_k, new_k in moves.items():
        val = comp.pop(old_k)
        comp.setdefault(new_k, val)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if moves:
        print(f"[info] {game} 活动重排：完成记录 seq 迁移 "
              + "、".join(f"{a}→{b}" for a, b in moves.items()))
    if drops:
        print(f"[info] {game} 活动剔除：移除完成记录 "
              + "、".join(f"{k}({n})" for k, n in drops))


def apply_manual_activities(game, payload):
    """回填 AI 人工解读的活动内容（--apply-json）。
    payload: {"game":.., "title":.., "version_start":.., "version_end":.., "post_id":..,
              "activities":[{"name","start","end"}...]}
    返回写入后的 cache 或 None。"""
    path = os.path.join(CACHE_DIR, f"{game}.json")
    if not os.path.exists(path):
        print(f"[error] 无缓存: {path}")
        return None
    cache = json.load(open(path, encoding="utf-8"))
    t = now()
    old_acts = [dict(a) for a in cache.get("activities", [])]
    version_switched = False
    for fld in ("title", "version_start", "version_end", "post_id"):
        val = payload.get(fld)
        if val and val != cache.get(fld):
            if fld == "title":
                version_switched = True
            cache[fld] = val
    raw = payload.get("activities") or []
    version_acts, kept_out = [], []
    for item in raw:
        name = (item.get("name") or "").strip()
        s, e = item.get("start", ""), item.get("end", "")
        if not name:
            continue
        hit, why = is_excluded_activity(name, item.get("desc", ""), game)
        if hit:
            kept_out.append((name, why))
            continue
        version_acts.append({
            "seq": 0, "name": name,
            "status": recompute_status(parse_dt(s), parse_dt(e), t),
            "type": "version", "fixed_key": "", "start": s, "end": e,
        })
    if not version_acts:
        print("[error] 回填内容为空，未修改缓存")
        return None
    if kept_out:
        print(f"[info] 回填时按规则剔除 {len(kept_out)} 项："
              + "、".join(f"{n}({w})" for n, w in kept_out))
    fixed = [a for a in old_acts if a.get("type") == "fixed"]
    fixed = local_recompute({"game": game, "title": cache.get("title"),
                             "version_start": cache.get("version_start"),
                             "version_end": cache.get("version_end"),
                             "activities": fixed}, t)
    cache["activities"] = sort_activities(version_acts + fixed)
    cache["cached_at"] = t.isoformat()
    json.dump(cache, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if version_switched:
        _cleanup_old_version_completed(game)
        sync_calendar(game, cache)
    else:
        _remap_completed_keys(game, old_acts, cache["activities"])
    print(f"[ok] {game} 已回填 {len(version_acts)} 条活动内容（按开始时间排序）")
    return cache


# ---------------- 游戏日历同步（版本切换时自动执行，2026-08-20 用户授权自动推送）----------------
# 游戏 key 映射 + gameTypes 元信息（新增游戏时在此追加一行即可）
CAL_GAME_META = {
    "绝区零": {"key": "zzz", "name": "绝区零", "bgImage": "./zzz/bg.png"},
    "鸣潮": {"key": "mc", "name": "鸣潮", "bgImage": "./mc/bg.jpeg"},
    "异环": {"key": "yh", "name": "异环", "bgImage": "./yh/bg.png"},
}
GAME_KEY = {g: m["key"] for g, m in CAL_GAME_META.items()}
# 日历仓库路径：优先环境变量；脚本若位于仓库内 scripts/ 子目录，则默认取仓库根目录。
CAL_PROJECT = os.environ.get("GAC_CAL_PROJECT") or (
    os.path.dirname(HERE) if os.path.basename(HERE) == "scripts"
    else r"D:\Lingfeng\gameCalendar")
EXCLUDE_KW = ["回归", "签到"]


def _to_cal_time(s):
    """缓存时间 → 日历格式 %Y-%m-%d %H（59 分进位到下一整点）。"""
    dt = parse_dt(s)
    if not dt:
        return (s or "").strip()
    if dt.minute >= 59:
        dt = dt + timedelta(minutes=1)
    return dt.strftime("%Y-%m-%d %H")


def _to_cal_date(s):
    dt = parse_dt(s)
    return dt.strftime("%Y/%m/%d") if dt else (s or "").strip()


def _classify_version(start_s, end_s):
    """版本活动按持续时间分类：≥25 天 → orange，<25 → gray。red 由用户手动维护，不在此生成。"""
    s, e = parse_dt(start_s), parse_dt(end_s)
    if not (s and e):
        return "gray"
    return "orange" if (e - s).days >= 25 else "gray"


def sync_calendar(game, cache, dry_run=False):
    """版本切换后同步游戏日历：转换 activities.json（保留 red、跳过 fixed/回归/签到、合并同起止），
    写回本地 → git commit → push gh-pages。返回 (changed, summary_text, pushed)。
    dry_run=True 时只计算并打印摘要，不写文件不提交。"""
    key = GAME_KEY.get(game)
    if not key:
        print(f"[warn] 同步跳过：未知游戏 {game}")
        return None, "未知游戏", False
    cal_path = os.path.join(CAL_PROJECT, "config", "activities.json")
    if not os.path.exists(cal_path):
        print(f"[warn] 同步跳过：日历项目不存在 {cal_path}")
        return None, "日历项目不存在", False
    data = json.load(open(cal_path, encoding="utf-8"))
    existing = data.get("gameData", {}).get(key, {}).get("activities", [])
    # 红色角色活动（限时频段/限时换取）由用户维护，原样保留并放最前
    red_acts = [a for a in existing if a.get("type") == "red"]
    # 从缓存生成版本活动（orange/gray），跳过 fixed 与排除关键词
    raw = []
    for a in cache.get("activities", []):
        if a.get("type") == "fixed":
            continue
        name = a.get("name", "")
        if any(k in name for k in EXCLUDE_KW):
            continue
        # 登录/签到类、绝区零潜能预演：缓存层已剔除，此处兜底再过滤一次
        if is_excluded_activity(name, "", game)[0]:
            continue
        raw.append({
            "name": name,
            "startTime": _to_cal_time(a.get("start", "")),
            "endTime": _to_cal_time(a.get("end", "")),
            "type": _classify_version(a.get("start", ""), a.get("end", "")),
            "icons": [], "hasDollarSign": False, "hasCharIcon": False, "charIcons": [],
        })
    # 合并同起止时间的活动（名称「、」连接，type 取 orange 优先）
    from collections import OrderedDict
    groups = OrderedDict()
    for a in raw:
        k = (a["startTime"], a["endTime"])
        groups.setdefault(k, []).append(a)
    version_acts = []
    for (st, et), group in groups.items():
        if len(group) == 1:
            version_acts.append(group[0])
        else:
            version_acts.append({
                "name": "、".join(a["name"] for a in group),
                "startTime": st, "endTime": et,
                "type": "orange" if any(a["type"] == "orange" for a in group) else "gray",
                "icons": [], "hasDollarSign": False, "hasCharIcon": False, "charIcons": [],
            })
    # 活动内容按开始时间升序（规则：修改活动内容时需按开始时间排序）
    version_acts.sort(key=lambda a: (a["startTime"], a["endTime"], a["name"]))
    new_acts = red_acts + version_acts
    data.setdefault("gameData", {}).setdefault(key, {})
    # gameTypes（日历的游戏选择项）缺失时自动补上，新增游戏无需手工改日历文件
    meta = CAL_GAME_META.get(game)
    if meta and "gameTypes" in data:
        if not any(t.get("key") == meta["key"] for t in data["gameTypes"]):
            data["gameTypes"].append(dict(meta))
            print(f"[info] {game} 已追加 gameTypes 项: {meta['key']}")
    data["gameData"][key]["calendarConfig"] = {
        "startDate": _to_cal_date(cache.get("version_start", "")),
        "endDate": _to_cal_date(cache.get("version_end", "")),
    }
    data["gameData"][key]["activities"] = new_acts
    new_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    old_text = open(cal_path, encoding="utf-8").read()
    changed = new_text != old_text
    summary = (f"  游戏: {game} ({key})\n"
               f"  版本区间: {cache.get('version_start', '')} ~ {cache.get('version_end', '')}\n"
               f"  版本活动数: {len(version_acts)}（red 角色活动 {len(red_acts)} 条原样保留）")
    if dry_run:
        print(f"[dry-run] {game} 日历转换{'有变更' if changed else '无变化'}\n{summary}")
        return changed, summary, False
    if not changed:
        print(f"[info] {game} activities.json 无变化，跳过同步")
        return False, summary, False
    open(cal_path, "w", encoding="utf-8").write(new_text)
    # git：确保 gh-pages 分支，仅提交 activities.json，提交并推送（用户已授权自动推送）
    subprocess.run(["git", "-C", CAL_PROJECT, "checkout", "gh-pages"], check=False)
    subprocess.run(["git", "-C", CAL_PROJECT, "add", "config/activities.json"], check=True)
    msg = f"chore: 同步 {game} 新版本活动 ({cache.get('version_start', '')}~{cache.get('version_end', '')})"
    r = subprocess.run(["git", "-C", CAL_PROJECT, "commit", "-m", msg], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[warn] {game} 日历 commit 失败（可能无变更）: {r.stderr.strip()[:200]}")
        return True, summary, False
    p = subprocess.run(["git", "-C", CAL_PROJECT, "push"], capture_output=True, text=True)
    if p.returncode != 0:
        print(f"[warn] {game} 日历 push 失败（沙箱可能限制 github.com）: {p.stderr.strip()[:200]}")
        print(f"[info] 本地文件与提交已就绪，请手动 push: git -C {CAL_PROJECT} push")
        return True, summary + "\n  ⚠️ 已本地提交，但 push 失败，需手动推送。", False
    print(f"[ok] {game} 日历已同步并推送 gh-pages\n{summary}")
    return True, summary + "\n  ✅ 已提交并推送 gh-pages", True


# ---------------- 图片解析：公告长图 OCR → 限时频段/限时换取 ----------------
# 触发点：公告获取（联网刷新成功）后自动执行；也可 --fetch-banners 手动执行。
# 绝区零源公告标题含【情报总览】；鸣潮标题含【版本资讯】。两者正文均为长图，必须 OCR。
# 依赖（隔离 venv）：rapidocr-onnxruntime + pillow + numpy
BANNER_SOURCE = {
    "绝区零": {"title_kw": "情报总览", "platform": "miyoushe",
              "suffix": "限时频段", "sep": "、", "dollar": True,
              "img_dir": "_intel_imgs", "icon_dir": "zzz"},
    "鸣潮": {"title_kw": "版本资讯", "platform": "kurobbs",
            "suffix": "限时换取", "sep": "/", "dollar": False,
            "img_dir": "_mc_news_imgs", "icon_dir": "mc"},
}

# charIcons 生成规则：文件名 = 角色名全量拼音小写（pypinyin）。
# 无条件写入（不校验本地 png 是否存在），缺失图标由用户按同名补图。
_ICON_WARNED = set()


def _char_icon(game, name):
    """charIcons 路径：./{icon_dir}/{角色名全量拼音小写}.png。"""
    src = BANNER_SOURCE.get(game) or {}
    icon_dir = src.get("icon_dir", "icons")
    if lazy_pinyin is None:
        if game not in _ICON_WARNED:
            _ICON_WARNED.add(game)
            print(f"[warn] {game} 缺 pypinyin，charIcons 暂以中文名命名（安装后重跑即纠正）")
        return f"./{icon_dir}/{name}.png"
    py = "".join(lazy_pinyin(name)).lower()
    return f"./{icon_dir}/{py}.png"


# 已知角色词库（OCR 名字纠错：全字命中 / 单字首字 / 尾字 / 等长首字，见 _fix_name）
# 维护要求：每个版本切换后把当期 UP 角色补进来，否则漏读与形近误读无法纠正。
_CHAR_LEXICON = {
    "绝区零": ["克拉蕾", "南宫羽", "洛克茜", "普罗米娅", "蕾米埃尔", "爱芮", "希格莉德", "千夏"],
    "鸣潮": ["清宵", "达妮娅", "景燃", "绯雪", "莫宁", "卡提希娅", "琳奈", "陆赫斯", "穗穗",
            "爱弥斯", "秧秧", "心月狐", "锁冥", "千咲", "尤诺", "洛瑟"],
}

# 人名多音字登记：pypinyin 默认读音与人名实际读音不符时在此补充
if load_phrases_dict is not None:
    load_phrases_dict({
        "洛克茜": [["luo"], ["ke"], ["xi"]],  # 茜读 xī（默认 qiàn）
    })
# zzz 卡片噪声词（卡片结构 [元素][名字][属性]RANK[英文名]）
_AGENT_STOPWORDS = {"锋御", "击破", "强攻", "支援", "异常", "防护", "代理人", "代理人定位",
                    "音擎", "代理人补强", "全新代理人", "UP", "RANK", "NEW"}
_ELEMENT_WORDS = {"以太", "物理", "流明", "霜烈", "烈霜", "电光", "妄想天使", "菲林", "母带"}
_IMG_RE = re.compile(r"https?://[^\"' )<>]+?\.(?:png|jpg|jpeg|webp)", re.I)


def ocr_image_tiled(path, tile_h=2000):
    """长图分块 OCR（整图会被缩放导致小字丢失），返回 [(y, score, text)] 按 y 升序。"""
    from rapidocr_onnxruntime import RapidOCR
    from PIL import Image
    import numpy as np
    ocr = RapidOCR()
    im = Image.open(path).convert("RGB")
    w, h = im.size
    out = []
    for y0 in range(0, h, tile_h):
        y1 = min(y0 + tile_h, h)
        arr = np.array(im.crop((0, y0, w, y1)))[:, :, ::-1]  # RGB -> BGR
        res, _ = ocr(arr)
        for r in (res or []):
            ys = [p[1] for p in r[0]]
            out.append((y0 + min(ys), float(r[2]), r[1]))
    out.sort()
    return out


def _ocr_region_enhanced(path, y0, y1, scale=3):
    """花字/低对比区域增强重扫：灰度 + autocontrast + 放大。返回 [(y, score, text)]。"""
    from rapidocr_onnxruntime import RapidOCR
    from PIL import Image, ImageOps
    import numpy as np
    ocr = RapidOCR()
    im = Image.open(path).convert("L")
    crop = ImageOps.autocontrast(im.crop((0, y0, im.size[0], y1)))
    crop = crop.resize((int(im.size[0] * scale), int((y1 - y0) * scale)), Image.LANCZOS)
    res, _ = ocr(np.array(crop))
    out = []
    for r in (res or []):
        ys = [p[1] for p in r[0]]
        out.append((y0 + min(ys) / scale, float(r[2]), r[1]))
    return out


def find_zzz_intel_post(max_pages=8):
    """米游社绝区零官方号翻页查找标题含「情报总览」的帖子。返回 (post_id, title, html)。"""
    h = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.miyoushe.com/"}
    base = "https://bbs-api.miyoushe.com/painter/wapi/userPostList?size=20&uid=152039148"
    offset = None
    for _ in range(max_pages):
        url = base + (f"&offset={offset}" if offset else "")
        lst = json.loads(_http_get(url, h))
        items = lst.get("data", {}).get("list", [])
        if not items:
            break
        for it in items:
            post = it.get("post", {})
            sub = post.get("subject", "")
            if BANNER_SOURCE["绝区零"]["title_kw"] in sub:
                pid = post.get("post_id")
                full = json.loads(_http_get(
                    f"https://bbs-api.miyoushe.com/post/wapi/getPostFull?post_id={pid}", h))
                html = full.get("data", {}).get("post", {}).get("post", {}).get("content", "")
                return pid, sub, html
        offset = items[-1].get("post", {}).get("post_id")
    return None


def find_mc_intel_post(max_pages=10):
    """库洛社区官方号翻页查找标题含「版本资讯」的帖子。返回 (post_id, title, html)。"""
    import urllib.parse
    h = _MC_HEADERS
    for page in range(1, max_pages + 1):
        body = urllib.parse.urlencode({"searchType": "1", "type": "2",
                                       "otherUserId": "10012001",
                                       "pageIndex": str(page), "pageSize": "20"}).encode()
        lst = json.loads(_http_get("https://api.kurobbs.com/forum/getMinePost", h, body))
        for p in lst.get("data", {}).get("postList", []):
            title = p.get("postTitle") or ""
            if BANNER_SOURCE["鸣潮"]["title_kw"] in title:
                pid = p.get("postId")
                body2 = urllib.parse.urlencode({"postId": str(pid), "isOnlyPublisher": "0",
                                                "showOrderType": "2"}).encode()
                det = json.loads(_http_get("https://api.kurobbs.com/forum/getPostDetail",
                                           h, body2))
                pd = det.get("data", {}).get("postDetail", {})
                html = pd.get("postH5Content") or pd.get("postContent") or ""
                return pid, title, html
    return None


def download_post_images(html, out_dir):
    """下载公告正文图片到 out_dir，返回本地路径列表。"""
    import urllib.request
    os.makedirs(out_dir, exist_ok=True)
    paths, seen = [], []
    for u in _IMG_RE.findall(html or ""):
        if u in seen:
            continue
        seen.append(u)
        p = os.path.join(out_dir, f"{len(paths) + 1}.{u.rsplit('.', 1)[-1].lower()}")
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            open(p, "wb").write(r.read())
        paths.append(p)
    return paths


def _cn_name(txt):
    """从 OCR 文本中提取纯中文名（2~4 字），去掉前缀 S / [ 等噪声。"""
    t = re.sub(r"^[Ss\[\]【】\s]+", "", (txt or "").strip())
    t = re.sub(r"[\[\]【】].*$", "", t).strip()
    if 2 <= len(t) <= 4 and re.fullmatch(r"[\u4e00-\u9fa5]+", t):
        return t
    return ""


def _fix_name(name, game):
    """OCR 名字纠错：全字命中直接用；否则依次尝试
    ① 单字首字匹配（心→心月狐，OCR 漏读尾部所致）；
    ② 尾字匹配（米雪→绯雪）；③ 等长首字匹配（锁膜→锁冥）。
    仅当候选唯一时才修正，多候选/零候选保持原样并告警。"""
    lex = _CHAR_LEXICON.get(game, [])
    if name in lex:
        return name
    if len(name) <= 1:
        cands = [k for k in lex if k.startswith(name)]
        if len(cands) == 1:
            print(f"[info] {game} OCR 名字修正: {name} → {cands[0]}（单字首字匹配）")
            return cands[0]
    else:
        for known in lex:
            if len(known) >= 2 and known.endswith(name[-1]):
                print(f"[info] {game} OCR 名字修正: {name} → {known}（尾字匹配）")
                return known
        cands = [k for k in lex if len(k) == len(name) and k[0] == name[0]]
        if len(cands) == 1:
            print(f"[info] {game} OCR 名字修正: {name} → {cands[0]}（等长首字匹配）")
            return cands[0]
    print(f"[warn] {game} UP 角色「{name}」不在已知角色库，请人工确认拼写")
    return name


def _parse_zzz_banners(lines, version_start=""):
    """绝区零【情报总览】：第X期调频 → 卡片 [元素][名字][属性]RANK[英文名]，RANK 锚点取名。"""
    vs = parse_dt(version_start)
    base_year = vs.year if vs else now().year
    base_month = vs.month if vs else 1

    def _mk_dt(mon, day, hh="", mm="", after_update=False):
        if after_update:
            return (vs, None) if vs else (None, None)
        year = base_year + (1 if mon < base_month - 6 else 0)
        if hh == "":
            d = parse_dt(f"{year}-{mon:02d}-{day:02d} 00:00")
            return d, d
        return parse_dt(f"{year}-{mon:02d}-{day:02d} {int(hh):02d}:{int(mm):02d}"), None

    banners, cur = [], None
    for y, score, txt in lines:
        t = txt.replace("：", ":").strip()
        m_ph = re.search(r"第([一二三四1-4])期调频", t)
        if m_ph:
            cur = {"phase": f"第{m_ph.group(1)}期", "names": [], "start": "", "end": ""}
            banners.append(cur)
            continue
        if cur is None:
            continue
        if "调频时间" in t or (not cur["start"] and "更新后" in t):
            m = re.search(r"(\d{1,2})月(\d{1,2})日更新后.{0,3}?"
                          r"(\d{1,2})月(\d{1,2})日(\d{1,2}):(\d{2})", t)
            if m:
                s, _ = _mk_dt(int(m.group(1)), int(m.group(2)), after_update=True)
                e, _ = _mk_dt(int(m.group(3)), int(m.group(4)), m.group(5), m.group(6))
                if s and e:
                    cur["start"], cur["end"] = _fmt(s), _fmt(e)
                continue
            m = re.search(r"(\d{1,2})月(\d{1,2})日(\d{1,2}):(\d{2}).{0,3}?"
                          r"(\d{1,2})月(\d{1,2})日(\d{1,2}):(\d{2})", t)
            if m:
                s, _ = _mk_dt(int(m.group(1)), int(m.group(2)), m.group(3), m.group(4))
                e, _ = _mk_dt(int(m.group(5)), int(m.group(6)), m.group(7), m.group(8))
                if s and e:
                    cur["start"], cur["end"] = _fmt(s), _fmt(e)
                continue
        if re.fullmatch(r"代理人(UP)?[!！]?", t):
            # 卡片结构：[元素] [名字] [属性] RANK [英文名] → RANK 锚点向上取最近中文名
            for y_r, _s_r, t_r in lines:
                if not (y < y_r <= y + 1600):
                    continue
                if not re.fullmatch(r"RANK", t_r.strip(), re.I):
                    continue
                cands = [(y2, _cn_name(t2)) for y2, sc2, t2 in lines
                         if y_r - 300 <= y2 < y_r and sc2 >= 0.5]
                cands = [(yy, nn) for yy, nn in cands
                         if nn and nn not in _AGENT_STOPWORDS and nn not in _ELEMENT_WORDS]
                if cands:
                    nm = max(cands, key=lambda c: c[0])[1]
                    if nm not in cur["names"]:
                        cur["names"].append(nm)
                break
            else:
                for y2, sc2, t2 in lines:
                    if y2 <= y or y2 > y + 1600 or sc2 < 0.55:
                        continue
                    nm = _cn_name(t2)
                    if not nm or nm in _AGENT_STOPWORDS or nm in _ELEMENT_WORDS \
                            or nm in cur["names"]:
                        continue
                    if any(y2 < y3 <= y2 + 300 and _cn_name(t3) in
                           ("锋御", "击破", "强攻", "支援", "异常", "防护")
                           for y3, _s3, t3 in lines):
                        cur["names"].append(nm)
                        break
    return [b for b in banners if b.get("names") and b.get("start") and b.get("end")]


def _parse_mc_banners(lines, version_start="", img_path=None, version_end=""):
    """鸣潮【版本资讯】：「角色武器活动唤取」期表头 → 活动时间 → {角色}UP! 卡片。
    时间行常为花字，分块 OCR 读不到时对该区域做增强重扫（灰度+autocontrast+放大）。"""
    vs = parse_dt(version_start)
    ve = parse_dt(version_end)

    def _mk_dt(y_, mon, day, hh, mm):
        year = y_ or (vs.year if vs else now().year)
        return parse_dt(f"{year}-{mon:02d}-{day:02d} {int(hh):02d}:{int(mm):02d}")

    def _collect_time(y_time):
        """「活动时间」标签之后收集起止时间；返回 (start, end)。"""
        dates, rel = [], False
        seg = [(yy, tt) for yy, _s, tt in lines if y_time < yy <= y_time + 300]
        if img_path:
            seg += [(yy, tt) for yy, _s, tt in
                    _ocr_region_enhanced(img_path, y_time, y_time + 300)]
        seg.sort()
        for _yy, tt in seg:
            t = tt.replace("：", ":")
            if "版本更新后" in t:
                rel = True
            for m in re.finditer(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})", t):
                dates.append((int(m.group(1) or 0), int(m.group(2)), int(m.group(3)),
                              int(m.group(4)), int(m.group(5))))
        if not dates and not rel:
            return None, None
        start = vs if (rel and vs) else None
        end = None
        if rel and dates:
            end = _mk_dt(dates[-1][0], dates[-1][1], dates[-1][2], dates[-1][3], dates[-1][4])
        elif len(dates) >= 2:
            start = _mk_dt(dates[0][0], dates[0][1], dates[0][2], dates[0][3], dates[0][4])
            end = _mk_dt(dates[-1][0], dates[-1][1], dates[-1][2], dates[-1][3], dates[-1][4])
        elif dates:
            end = _mk_dt(dates[0][0], dates[0][1], dates[0][2], dates[0][3], dates[0][4])
        return start, (end or ve)

    banners, cur = [], None
    for y, score, txt in lines:
        t = txt.strip()
        # 期表头：角色武器活动唤取 / 角色/武器活动唤取（区别于单张卡片的「角色活动唤取」）
        if re.search(r"角色.{0,3}武器.{0,3}活动唤取", t):
            cur = {"phase": f"第{len(banners) + 1}期", "names": [], "start": "", "end": ""}
            banners.append(cur)
            continue
        if cur is None:
            continue
        if re.fullmatch(r"活动时间", t) and not cur["start"]:
            s, e = _collect_time(y)
            if s:
                cur["start"] = _fmt(s)
            if e:
                cur["end"] = _fmt(e)
            continue
        m = re.match(r"^[\s·小中]*([\u4e00-\u9fa5]{1,4})\s*UP\s*[!！]?", t)
        if m:
            nm = _fix_name(m.group(1), "鸣潮")
            if nm not in cur["names"]:
                cur["names"].append(nm)
    return [b for b in banners if b.get("names") and b.get("start") and b.get("end")]


def parse_banners_from_ocr(lines, version_start="", game="绝区零",
                           img_path=None, version_end=""):
    if game == "鸣潮":
        return _parse_mc_banners(lines, version_start, img_path, version_end)
    return _parse_zzz_banners(lines, version_start)


def build_red_entries(banners, game):
    """按规则生成 red 角色活动条目：
    - 同起止时间的角色合并为一条（绝区零「、」/ 鸣潮「/」连接）
    - charIcons 无条件写入：文件名 = 角色名全量拼音小写
    """
    src = BANNER_SOURCE[game]
    groups = {}
    for b in banners:
        key = (b["start"], b["end"])
        groups.setdefault(key, [])
        for n in b["names"]:
            if n not in groups[key]:
                groups[key].append(n)
    entries = []
    for (s, e), names in sorted(groups.items()):
        icons = []
        for n in names:
            rel = _char_icon(game, n)
            if rel and rel not in icons:
                icons.append(rel)
        entries.append({
            "name": src["sep"].join(names) + f" - {src['suffix']}",
            "startTime": _to_cal_time(s),
            "endTime": _to_cal_time(e),
            "type": "red", "icons": [],
            "hasDollarSign": src["dollar"],
            "hasCharIcon": bool(icons),
            "charIcons": icons,
        })
    return entries


def fetch_banner_data(game, version_start="", version_end=""):
    """抓取该游戏的卡池源公告 → 下载图片 → 分图 OCR → 解析。返回 meta+banners 或 None。"""
    src = BANNER_SOURCE.get(game)
    if not src:
        return None
    got = find_zzz_intel_post() if src["platform"] == "miyoushe" else find_mc_intel_post()
    if not got:
        print(f"[warn] {game} 未找到标题含「{src['title_kw']}」的公告")
        return None
    pid, title, html = got
    print(f"[ok] {game} 公告: {title} (post_id={pid})")
    imgs = download_post_images(html, os.path.join(CACHE_DIR, src["img_dir"]))
    print(f"[ok] {game} 下载图片 {len(imgs)} 张")
    banners = []
    for p in imgs:
        lines = ocr_image_tiled(p)
        got_b = parse_banners_from_ocr(lines, version_start, game,
                                       img_path=p, version_end=version_end)
        print(f"[ok] {game} OCR {os.path.basename(p)} → {len(lines)} 行，解析 {len(got_b)} 期")
        for b in got_b:
            if b not in banners:
                banners.append(b)
    return {"post_id": str(pid), "title": title, "banners": banners}


def _apply_red_entries(game, new_red):
    """把 red 条目写入 activities.json（删旧 red → 写新 → commit → push）。返回是否变更。"""
    cal_path = os.path.join(CAL_PROJECT, "config", "activities.json")
    if not os.path.exists(cal_path):
        print(f"[warn] 日历项目不存在，跳过写入: {cal_path}")
        return False
    key = GAME_KEY[game]
    data = json.load(open(cal_path, encoding="utf-8"))
    blk = data.setdefault("gameData", {}).setdefault(key, {})
    old_red = [a for a in blk.get("activities", []) if a.get("type") == "red"]
    if old_red == new_red:
        print(f"[info] {game} red 条目无变化")
        return False
    blk["activities"] = new_red + [a for a in blk.get("activities", [])
                                   if a.get("type") != "red"]
    open(cal_path, "w", encoding="utf-8").write(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    subprocess.run(["git", "-C", CAL_PROJECT, "checkout", "gh-pages"], check=False)
    subprocess.run(["git", "-C", CAL_PROJECT, "add", "config/activities.json"], check=True)
    msg = f"chore: 同步 {game} 限时角色活动（公告获取自动更新）"
    r = subprocess.run(["git", "-C", CAL_PROJECT, "commit", "-m", msg],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[warn] {game} 日历 commit 失败: {r.stderr.strip()[:200]}")
        return True
    p = subprocess.run(["git", "-C", CAL_PROJECT, "push"], capture_output=True, text=True)
    if p.returncode == 0:
        print(f"[ok] {game} red 条目已写入并推送 gh-pages")
    else:
        print(f"[warn] {game} push 失败，需手动推送: {p.stderr.strip()[:200]}")
    return True


def refresh_red_entries(game, apply=True):
    """公告获取触发点：抓源公告 → OCR → 解析 → 更新 red 条目（旧 red 全删）。"""
    if game not in BANNER_SOURCE:
        return None  # 未配置卡池源公告的游戏（如异环，角色源待接入）跳过
    cache_path = os.path.join(CACHE_DIR, f"{game}.json")
    vstart = vend = ""
    if os.path.exists(cache_path):
        c = json.load(open(cache_path, encoding="utf-8"))
        vstart, vend = c.get("version_start", ""), c.get("version_end", "")
    data = fetch_banner_data(game, vstart, vend)
    if not data or not data["banners"]:
        print(f"[warn] {game} 未能从公告解析出限时角色活动")
        return None
    for b in data["banners"]:
        print(f"  {b['phase']}: {'、'.join(b['names'])}  {b['start']} ~ {b['end']}")
    new_red = build_red_entries(data["banners"], game)
    if apply:
        _apply_red_entries(game, new_red)
    return new_red


def cmd_fetch_banners(games, apply=False):
    """手动入口：抓取各游戏的限时角色活动（默认仅预览）。"""
    for game in games:
        if game not in BANNER_SOURCE:
            print(f"[skip] {game} 未配置卡池源公告")
            continue
        new_red = refresh_red_entries(game, apply=apply)
        if new_red is None:
            continue
        out = os.path.join(HERE, f"_banners_preview_{game}.json")
        json.dump({"red_after": new_red}, open(out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"[ok] {game} 预览: {out}")
    if not apply:
        print("[info] 仅预览，未修改 activities.json。加 --apply 才会写入并 commit/push。")


# ---------------- 主流程 ----------------
def _cache_expired(cache, t):
    """本地缓存是否过期（版本已结束）。无 version_end 视为过期需联网。"""
    vend = parse_dt(cache.get("version_end"))
    if vend is None:
        return True
    return t >= vend


def refresh_game(game, t, allow_network=True, force_network=False):
    path = os.path.join(CACHE_DIR, f"{game}.json")
    if not os.path.exists(path):
        print(f"[skip] 无缓存: {path}")
        return
    cache = json.load(open(path, encoding="utf-8"))
    alerts = []

    old_acts = [dict(a) for a in cache.get("activities", [])]
    new_acts = local_recompute(cache, t)  # 内含按开始时间排序
    cache["activities"] = new_acts
    used_network = False
    version_switched = False

    expired = _cache_expired(cache, t)
    # 按需联网：仅缓存过期（版本结束）才去抓新公告；未过期只本地重算
    if allow_network and (expired or force_network):
        net, alert = network_refresh(game, cache, t)
        if net:
            used_network = True
            cache["post_id"] = net.get("post_id", cache.get("post_id"))
            if net.get("title"):
                cache["title"] = net["title"]
            if net.get("version_start"):
                cache["version_start"] = net["version_start"]
            if net.get("version_end"):
                cache["version_end"] = net["version_end"]
            cache["activities"] = net["activities"]
            # 公告获取成功 → 同步更新限时频段/限时换取（新角色进旧角色清）
            try:
                refresh_red_entries(game, apply=True)
            except ImportError as ex:
                print(f"[warn] {game} 限时角色活动更新跳过（缺 OCR 依赖，"
                      f"请改用 envs/default 解释器运行）: {ex}")
            except Exception as ex:
                print(f"[warn] {game} 限时角色活动自动更新失败: {ex}")
            if alert:
                version_switched = True
                # 版本切换：清理旧版本活动完成记录，避免 seq 复用误判已完成
                _cleanup_old_version_completed(game)
                # 版本切换：自动同步游戏日历（转换 activities.json + commit + push gh-pages）
                synced = sync_calendar(game, cache)
                # 仅在同步/推送未成功时保留「请手动同步」提示（同步成功则该提示已过时）
                if not (synced and synced[2]):
                    alerts.append(alert)
        # 联网失败/未通过校验则保持本地重算结果

    if not version_switched:
        # 活动内容重排/剔除后，同步迁移完成记录的 seq，避免完成状态错位
        _remap_completed_keys(game, old_acts, cache.get("activities", []))

    cache["cached_at"] = t.isoformat()
    json.dump(cache, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 完成态对照
    completed = _load_completed()
    done_active, doing, upcoming, ended = [], [], [], []
    n_done = 0
    for a in cache["activities"]:
        is_done = _completion_key(game, a) in completed
        a = dict(a)
        a["_done"] = is_done
        if is_done:
            n_done += 1
        if a["status"] == "ended":
            ended.append(a)
        elif a["status"] == "upcoming" and not is_done:
            upcoming.append(a)
        elif is_done:
            done_active.append(a)
        else:
            doing.append(a)

    n_total = len(cache["activities"])
    src = "network" if used_network else "local-recompute"
    print(f"[ok] {game}: 来源={src} 已完成={n_done}/{n_total}  "
          f"进行中未做={len(doing)} 即将开始={len(upcoming)} 已结束={len(ended)}")

    def _line(a):
        tag = "✅" if a["_done"] else ("🔸" if a["status"] == "active" else "⏳")
        return (f"     {tag} #{a['seq']:2d} {a['name']}  "
                f"end={a['end']}  ({a['start']} ~ {a['end']})")

    if done_active:
        print(f"  ── 已完成（活动还在）{len(done_active)}")
        for a in done_active:
            print(_line(a))
    if doing:
        print(f"  ── 进行中未完成 {len(doing)}")
        for a in doing:
            print(_line(a))
    if upcoming:
        print(f"  ── 即将开始 {len(upcoming)}")
        for a in upcoming:
            print(_line(a))
    if ended:
        done_ended = [a for a in ended if a["_done"]]
        if done_ended:
            print(f"  ── 已完成（活动已结束）{len(done_ended)}")
            for a in done_ended:
                print(_line(a))
        pending_ended = [a for a in ended if not a["_done"]]
        if pending_ended:
            print(f"  ── 已结束（漏做？）{len(pending_ended)}")
            for a in pending_ended:
                print(_line(a))

    for al in alerts:
        print(al)


def _plain_text(html):
    txt = re.sub(r"<[^>]+>", "\n", _normalize_dt_text(html))
    return "\n".join(l.strip() for l in txt.split("\n") if l.strip())


def cmd_parse_only(games):
    """联网抓取并展示解析结果（不写缓存），用于人工/AI 抽查解析是否正确。"""
    for game in games:
        fetcher = FETCHERS.get(game)
        if not fetcher:
            print(f"[skip] {game} 未配置公告抓取器")
            continue
        res = fetcher()
        if not res:
            print(f"[error] {game} 抓取失败")
            continue
        post_id, title, html = res
        nhtml = _plain_text(html)
        vstart = infer_version_start(html, "")
        vend = infer_version_end(html, vstart, "")
        cands, excluded = parse_activities_from_html(html, vstart, vend or "", game)
        ok, why = validate_parse(nhtml, cands, len(excluded), vstart)
        print(f"\n=== {game} | {title} | post_id={post_id} ===")
        print(f"版本区间: {vstart} ~ {vend}  解析={len(cands)} 条  剔除={len(excluded)} 条"
              f"  校验={'通过' if ok else '未通过 ' + '；'.join(why)}")
        for i, (n, s, e) in enumerate(sorted(cands, key=lambda x: (x[1], x[2])), 1):
            print(f"  #{i} {n}  ({s} ~ {e})")
        for n, w in excluded:
            print(f"  ✗ 已剔除 {n} — {w}")
        if not ok:
            p = os.path.join(CACHE_DIR, f"_announcement_{game}.txt")
            open(p, "w", encoding="utf-8").write(nhtml)
            print(f"NEEDS_LLM_PARSE: {game} 公告原文已导出到 {p}")


def main():
    t = now()
    status_path = os.path.join(CACHE_DIR, "game-status.json")
    allow_network = "--no-network" not in sys.argv
    force_network = "--force-network" in sys.argv
    if not os.path.exists(status_path):
        print("[error] 缺少 game-status.json")
        sys.exit(1)
    st = json.load(open(status_path, encoding="utf-8"))
    games = [g for g, v in st.get("games", {}).items() if v.get("status") == "playing"]

    # --apply-json <file>：回填 AI 人工解读的活动内容
    if "--apply-json" in sys.argv:
        fp = sys.argv[sys.argv.index("--apply-json") + 1]
        payload = json.load(open(fp, encoding="utf-8"))
        g = payload.get("game") or (games[0] if games else "")
        apply_manual_activities(g, payload)
        return
    # --dump-text [game]：只抓取并导出公告纯文本
    if "--dump-text" in sys.argv:
        for g in games:
            _fetcher = FETCHERS.get(g)
            res = _fetcher() if _fetcher else None
            if not res:
                print(f"[error] {g} 抓取失败")
                continue
            p = os.path.join(CACHE_DIR, f"_announcement_{g}.txt")
            open(p, "w", encoding="utf-8").write(_plain_text(res[2]))
            print(f"[ok] {g} 公告已导出: {p}")
        return
    # --fetch-banners [--apply] [--game X]：源公告 OCR → 限时频段/限时换取（默认仅预览）
    if "--fetch-banners" in sys.argv:
        target = [sys.argv[sys.argv.index("--game") + 1]] if "--game" in sys.argv else games
        cmd_fetch_banners(target, apply="--apply" in sys.argv)
        return
    # --parse-only：解析抽查（不写缓存）
    if "--parse-only" in sys.argv:
        cmd_parse_only(games)
        return

    mode = "强制联网" if force_network else ("开(仅版本过期时联网)" if allow_network else "关")
    print(f"=== 缓存刷新 {t.strftime('%Y-%m-%d %H:%M')} 游戏: {games} 联网={mode} ===")
    for g in games:
        try:
            refresh_game(g, t, allow_network, force_network)
        except Exception as ex:
            print(f"[error] {g}: {ex}")
    print("=== 完成 ===")


if __name__ == "__main__":
    main()
