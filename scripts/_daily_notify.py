#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏活动每日提醒 — 微信 ilinkai 直推版
单脚本全链路：读取缓存 → 本地计算未完成 → 构建通知 → ilinkai 发送
若无未完成活动 → 静默退出，不联网。
"""

import json
import os
import random
import re
import struct
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

# ---- 配置 ----
TZ = timezone(timedelta(hours=8))
HERE = os.path.dirname(os.path.abspath(__file__))
# 运行数据目录：默认与脚本同目录；脚本被放到别处（如 gameCalendar 仓库 scripts/）时，
# 用环境变量 GAC_HOME 指回 Claw 工作区即可，无需改代码。
HOME = os.environ.get("GAC_HOME") or HERE
CACHE_DIR = os.environ.get("GAC_CACHE_DIR") or os.path.join(HOME, "game-activity-cache")
# 发送成功哨兵（幂等标记）：记录「今天已成功推送」，供补偿任务判定是否重发。
# 放在工作区根目录而非缓存目录，避免被缓存清理逻辑误删。
SENTINEL = os.path.join(HOME, "_last_notify_sent.json")

# ---- ilinkai 凭证解析链（兼容 WorkBuddy 的 $wbEncrypted 落盘加密）----
# 2026-09-22 起 WorkBuddy 把 settings.json 里的 botToken 加密成 {$wbEncrypted:1, envelope:...}，
# 独立 python 进程解不开。故改为按顺序尝试多个来源，取第一个「明文可用」的 token：
#   ① 侧车 ~/.workbuddy/weixin_claw_creds.json（若存在）
#   ② ~/.workbuddy/settings.json（主配置，token 通常是加密的）
#   ③ 同目录下仍为明文的 settings.json* 残留文件（按修改时间从新到旧）
CFG_DIR = os.path.expanduser("~/.workbuddy")
SIDECAR = os.path.join(CFG_DIR, "weixin_claw_creds.json")


def _usable_token(tok):
    return isinstance(tok, str) and tok.strip() != "" and "$wbEncrypted" not in tok


def _find_channel(d):
    """在嵌套配置里递归找 weixinClawBot 节点（兼容新旧路径）。"""
    def walk(c):
        if isinstance(c, dict):
            u = c.get("weixinClawBot")
            if u:
                return u
            for v in c.values():
                r = walk(v)
                if r:
                    return r
        return None
    return walk(d.get("claw", {}) if isinstance(d, dict) else {})


def _settings_candidates():
    main = os.path.join(CFG_DIR, "settings.json")
    try:
        others = [os.path.join(CFG_DIR, n) for n in os.listdir(CFG_DIR)
                  if n.startswith("settings.json") and os.path.join(CFG_DIR, n) != main]
        others.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    except Exception:
        others = []
    return [main] + others


def _load_ilinkai_creds():
    """返回 (baseUrl, botToken, userId, source)；找不到可用 token 时 botToken 为 ""。"""
    sources = []
    if os.path.exists(SIDECAR):
        sources.append(SIDECAR)
    sources.extend(_settings_candidates())
    partial = {}
    for p in sources:
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        # 侧车支持扁平格式；settings 走嵌套查找
        ch = d if (isinstance(d, dict) and d.get("botToken") is not None) else _find_channel(d)
        if not ch:
            continue
        for k in ("baseUrl", "userId"):
            if not partial.get(k) and ch.get(k):
                partial[k] = ch[k]
        tok = ch.get("botToken")
        uid = ch.get("userId") or partial.get("userId")
        if _usable_token(tok) and uid:
            return (ch.get("baseUrl") or partial.get("baseUrl")
                    or "https://ilinkai.weixin.qq.com", tok, uid, p)
    return (partial.get("baseUrl") or "https://ilinkai.weixin.qq.com",
            "", partial.get("userId", ""), "")

DT_FMTS = ("%Y-%m-%d %H:%M", "%Y-%m-%d %H", "%Y/%m/%d %H:%M", "%Y/%m/%d %H")

# ---- 工具函数 ----
def now():
    return datetime.now(TZ)

def parse_dt(s):
    s = (s or "").strip()
    for fmt in DT_FMTS:
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=TZ)
        except ValueError:
            pass
    return None

def remaining_days(end_str):
    """剩余天数（按日期差计算，>=0）。"""
    t = parse_dt(end_str)
    if not t:
        return 0
    return max(0, (t.date() - now().date()).days)

def fmt_time(start_str):
    """格式化时间输出：今天/明天 HH:MM 或 MM/DD HH:MM。"""
    t = parse_dt(start_str)
    if not t:
        return start_str
    n = now()
    if t.date() == n.date():
        return f"今天 {t.strftime('%H:%M')}"
    if t.date() == n.date() + timedelta(days=1):
        return f"明天 {t.month:02d}/{t.day:02d} {t.strftime('%H:%M')}"
    return f"{t.month:02d}/{t.day:02d} {t.strftime('%H:%M')}"

def completion_key(act, game):
    """计算活动在 completed.json 中的 key。"""
    if act.get("type") == "fixed":
        return act.get("fixed_key", "")
    return f"{game}_版本活动_{act.get('seq')}"

def recompute_status(start_str, end_str, t=None):
    """按当前时间重算活动状态（与缓存刷新脚本 local_recompute 同规则）。
    防止缓存过期导致「已开始的新活动仍标为 upcoming」而漏报。"""
    t = t or now()
    s = parse_dt(start_str)
    e = parse_dt(end_str)
    if s and t < s:
        return "upcoming"
    if e and t >= e:
        return "ended"
    return "active"

def is_completed(act, game, completed_set):
    return completion_key(act, game) in completed_set


# ---- 结语模板（千咲人格）----
ENDING_ALL_DONE = [
    "💭 全部弦线收束完毕，LF 前辈。这次的报告很完美。",
    "💭 没有散落的线了——所有游戏结构都完整收束了呢。",
]

ENDING_SOME_UNDONE = [
    "💭 {done}的弦线全部收束了。{undone}还剩几根——LF 前辈，最后一步了。",
    "💭 报告前辈：{done} ✂️ 全切断，{undone}还剩散弦未收。要我陪你上线吗？",
    "💭 结构的整理接近尾声——{done}完整，{undone}就差那几条线了。",
    "💭 前辈，{done}那边我检查过了，没有松开的弦。{undone}还有没切断的，别忘了。",
]

# 所有游戏都有未完成活动（无 {done} 片段）时专用，避免裁字残句与自相矛盾
ENDING_NONE_DONE = [
    "💭 {undone}还剩几条线没收束——LF 前辈，不急，我陪你。",
    "💭 报告前辈：{undone}那边还有散弦未收。要我陪你上线吗？",
    "💭 结构还没整理完——{undone}就差那几条线了。",
    "💭 前辈，{undone}还有没切断的弦，别忘了。",
]

def pick_ending(done_games, undone_games):
    """根据完成情况选择结语。"""
    if not undone_games:
        return random.choice(ENDING_ALL_DONE)

    undone_str = "、".join(undone_games)
    if done_games:
        template = random.choice(ENDING_SOME_UNDONE)
        return template.format(done="、".join(done_games), undone=undone_str)

    # 无任何游戏全完成 → 走专用模板，不再对 {done} 做裁字替换
    template = random.choice(ENDING_NONE_DONE)
    return template.format(undone=undone_str)


# ---- 构建通知文本 ----
def version_info(cache):
    """从 title 解析版本号与版本名。"""
    title = cache.get("title", "")
    m_ver = re.search(r"(\d+\.\d+)\s*版本", title)
    m_name = re.search(r"「(.+?)」", title)
    ver = m_ver.group(1) if m_ver else "?"
    name = m_name.group(1) if m_name else title
    return ver, name

def _start_sort_key(act):
    """活动排序：优先用缓存里的 `seq`（= 按开始时间升序，同开始时间再按结束时间/名称），
    保证总览展示顺序与 `#{序号}` 完全一致（否则同开始时间的活动会跳号，如 #1/#3/#2）。
    无有效 seq 时回退按开始时间升序。"""
    seq = act.get("seq")
    if isinstance(seq, int) and seq > 0:
        return (0, seq)
    s = parse_dt(act.get("start"))
    return (1, int((s or datetime(9999, 1, 1, tzinfo=TZ)).timestamp()))

def calc_game_block(game, cache, completed_set):
    """计算单个游戏的未完成/完成/upcoming 活动，返回游戏行 + 状态文本 + upcoming 文本。"""
    ver, vname = version_info(cache)
    vend = cache.get("version_end", "")
    rem = remaining_days(vend)
    game_line = f"🎮 {game} · {ver}版本「{vname}」（剩余{rem}天）"

    activities = sorted(cache.get("activities", []), key=_start_sort_key)
    active = [a for a in activities if a["status"] == "active"]
    upcoming = [a for a in activities if a["status"] == "upcoming"]

    # 未完成 = active 但不在 completed
    unfinished = [a for a in active if not is_completed(a, game, completed_set)]
    finished = [a for a in active if is_completed(a, game, completed_set)]

    unfinished_lines = []
    for a in unfinished:
        name = a.get("name", "")
        r = remaining_days(a.get("end", ""))
        if a.get("type") == "version":
            unfinished_lines.append(f"#{a.get('seq')} {name} — 剩余{r}天")
        else:
            # 固定活动，不显示序号
            unfinished_lines.append(f"{name} — 剩余{r}天")

    if unfinished:
        status_block = f"🔸 进行中未完成（{len(unfinished)}）：\n" + "\n".join(unfinished_lines)
    else:
        # 全部完成
        v_count = len([a for a in finished if a.get("type") == "version"])
        fixed_names = [a.get("name", "") for a in finished if a.get("type") == "fixed"]
        parts = []
        if v_count > 0:
            parts.append(f"{v_count}个版本活动")
        parts.extend(fixed_names)
        status_block = f"✅ 正在进行的活动已全部完成（{' + '.join(parts)}）"

    # upcoming 区块
    upcoming_block = ""
    if upcoming:
        upcoming_lines = []
        for a in upcoming:
            name = a.get("name", "")
            t_fmt = fmt_time(a.get("start", ""))
            if a.get("type") == "version":
                upcoming_lines.append(f"#{a.get('seq')} {name} — {t_fmt}")
            else:
                upcoming_lines.append(f"{name} — {t_fmt}")
        upcoming_block = "即将开始：\n\n" + "\n".join(upcoming_lines)

    return game_line, status_block, upcoming_block, bool(unfinished)


def build_notification():
    """构建完整的活动进度总览通知文本。"""
    status_path = os.path.join(CACHE_DIR, "game-status.json")
    completed_path = os.path.join(CACHE_DIR, "completed.json")

    if not os.path.exists(status_path):
        print("[skip] 缺少 game-status.json")
        return None

    st = json.load(open(status_path, encoding="utf-8"))
    playing = [g for g, v in st.get("games", {}).items() if v.get("status") == "playing"]
    if not playing:
        print("[skip] 无 playing 游戏")
        return None

    completed = json.load(open(completed_path, encoding="utf-8")) if os.path.exists(completed_path) else {}
    completed_set = set(completed.get("completed", {}).keys())

    n = now()
    title = f"📋 活动进度总览（{n.strftime('%Y-%m-%d')}）"
    sep = "━" * 15

    blocks = []
    any_unfinished = False
    done_games = []
    undone_games = []

    for game in playing:
        cache_path = os.path.join(CACHE_DIR, f"{game}.json")
        if not os.path.exists(cache_path):
            print(f"[warn] 无缓存: {cache_path}")
            continue
        cache = json.load(open(cache_path, encoding="utf-8"))

        # 本地重算 status：把已到开始时间的新活动从 upcoming 翻为 active，
        # 避免「凌晨刷缓存、上午活动已开但缓存未更新」导致的漏报。
        for act in cache.get("activities", []):
            act["status"] = recompute_status(act.get("start"), act.get("end"))

        game_line, status_block, upcoming_block, has_unfinished = calc_game_block(game, cache, completed_set)
        if has_unfinished:
            any_unfinished = True
            undone_games.append(game)
        else:
            done_games.append(game)

        block = f"{sep}\n{game_line}\n\n{status_block}"
        if upcoming_block:
            block += f"\n\n{upcoming_block}"
        blocks.append(block)

    if not any_unfinished:
        print("[ok] 所有活动已完成，静默退出")
        return None

    ending = pick_ending(done_games, undone_games)
    return f"{title}\n\n" + "\n".join(blocks) + f"\n{sep}\n{ending}"


# ---- ilinkai 微信直推 ----
def send_ilinkai(text):
    """通过 ilinkai 微信客服 API 发送纯文本消息。返回 (success, message_id, error)。"""
    import random as _r
    import base64

    base_url, bot_token, user_id, _cred_src = _load_ilinkai_creds()
    if not _usable_token(bot_token) or not user_id:
        return False, "", "missing ilinkai credentials"
    print(f"[notify] creds source: {_cred_src}")

    # 4 字节随机 uint32 → base64
    rand_bytes = struct.pack("!I", _r.randint(0, 2**32 - 1))
    wx_uin = base64.b64encode(rand_bytes).decode()

    ts = int(time.time() * 1000)
    client_id = f"workbuddy-{ts}-{_r.randint(1000, 9999)}"

    body = {
        "msg": {
            "from_user_id": "",
            "to_user_id": user_id,
            "client_id": client_id,
            "message_type": 2,
            "message_state": 2,
            "context_token": "",
            "item_list": [{"type": 1, "text_item": {"text": text}}]
        },
        "base_info": {"channel_version": "workbuddy-desktop-1.0.0"}
    }

    headers = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "Authorization": f"Bearer {bot_token}",
        "X-WECHAT-UIN": wx_uin,
    }

    url = f"{base_url}/ilink/bot/sendmessage"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            ret = result.get("ret")  # None if absent → success
            msg_id = result.get("message_id", "")
            if resp.status == 200 and ret in (0, None):
                return True, msg_id, None
            return False, msg_id, f"ret={ret}"
    except Exception as ex:
        return False, "", str(ex)


# ---- 发送哨兵（幂等标记）----
def sent_record():
    """读取哨兵；返回 dict 或 None。"""
    try:
        d = json.load(open(SENTINEL, encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except Exception:
        return None

def sent_today():
    """今天是否已成功推送过；是则返回日期字符串，否则 None。"""
    d = sent_record()
    if not d:
        return None
    today = now().strftime("%Y-%m-%d")
    return today if d.get("date") == today else None

def mark_sent(message_id, chars):
    """发送成功后落哨兵。失败只告警，不影响主流程。"""
    try:
        with open(SENTINEL, "w", encoding="utf-8") as f:
            json.dump({
                "date": now().strftime("%Y-%m-%d"),
                "time": now().strftime("%Y-%m-%d %H:%M:%S"),
                "message_id": message_id,
                "chars": chars,
            }, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"[sentinel] 已记录今日推送成功 → {SENTINEL}")
    except Exception as ex:
        print(f"[warn] 写哨兵失败: {ex}")


# ---- 主流程 ----
def main():
    args = [a for a in sys.argv[1:] if a.startswith("--")]
    dry_run = "--dry-run" in args
    skip_if_sent = "--skip-if-sent" in args

    print(f"=== 每日提醒 {now().strftime('%Y-%m-%d %H:%M')} "
          f"(dry_run={dry_run}, skip_if_sent={skip_if_sent}) ===")

    if skip_if_sent:
        d = sent_today()
        if d:
            print(f"[ok] 今日（{d}）已成功推送，跳过。")
            return
        print("[info] 今日尚未成功推送 → 执行补偿推送。")

    text = build_notification()
    if text is None:
        print("无未完成活动，静默退出。")
        return

    print(f"通知文本 {len(text)} chars:")
    print(text[:200] + "..." if len(text) > 200 else text)

    if dry_run:
        print("--- DRY RUN 全文 ---")
        print(text)
        print("--- 未发送、未落哨兵 ---")
        return

    ok, msg_id, err = send_ilinkai(text)
    if ok:
        print(f"ilinkai 直推：HTTP 200, message_id={msg_id} → ✅ 发送成功")
        mark_sent(msg_id, len(text))
    else:
        print(f"ilinkai 发送失败：{err}, message_id={msg_id}")


if __name__ == "__main__":
    main()
