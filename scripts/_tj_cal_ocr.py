# -*- coding: utf-8 -*-
"""临时脚本：抓取塔吉多帖子图片并分块 OCR（异环 1.4 活动日历）。"""
import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HDR = {"User-Agent": UA, "Referer": "https://www.tajiduo.com/"}
HERE = os.path.dirname(os.path.abspath(__file__))
# 运行数据目录：默认与脚本同目录；脚本被放到别处（如 gameCalendar 仓库 scripts/）时，
# 用环境变量 GAC_HOME 指回 Claw 工作区即可，无需改代码。
HOME = os.environ.get("GAC_HOME") or HERE
CACHE_DIR = os.environ.get("GAC_CACHE_DIR") or os.path.join(HOME, "game-activity-cache")
IMGDIR = os.path.join(CACHE_DIR, "_tj_imgs")


def get_json(url):
    req = urllib.request.Request(url, headers=HDR)
    return json.load(urllib.request.urlopen(req, timeout=25))


def list_posts(cursor=0):
    d = get_json(f"https://bbs-api.tajiduo.com/bbs/wapi/getUserPostList?uid=10100006&version={cursor}")
    return d.get("data", {})


def collect_images(post):
    sc = post.get("structuredContent") or ""
    urls = []
    try:
        blocks = json.loads(sc)
    except Exception:
        return urls
    for b in blocks:
        if not isinstance(b, dict):
            continue
        for k in ("image", "img", "url", "src"):
            v = b.get(k)
            if isinstance(v, str) and v.startswith("http"):
                urls.append(v)
        for v in b.values():
            if isinstance(v, dict):
                for k2 in ("url", "src", "image"):
                    v2 = v.get(k2)
                    if isinstance(v2, str) and v2.startswith("http"):
                        urls.append(v2)
    return urls


def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 493493
    data = list_posts(0)
    post = None
    for p in data.get("posts", []):
        if p.get("postId") == target:
            post = p
            break
    if not post:
        print("post not found in page 1:", target)
        return
    print("subject:", post.get("subject"))
    urls = collect_images(post)
    print("image urls:", len(urls))
    for u in urls:
        print("  ", u)
    if not urls:
        # 打印 block 结构辅助排查
        blocks = json.loads(post.get("structuredContent") or "[]")
        for i, b in enumerate(blocks):
            print(i, json.dumps(b, ensure_ascii=False)[:300])
        return
    os.makedirs(IMGDIR, exist_ok=True)
    import numpy as np
    from PIL import Image
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    for i, u in enumerate(urls):
        ext = ".png" if ".png" in u.lower() else ".jpg"
        path = os.path.join(IMGDIR, f"tj_{target}_{i}{ext}")
        req = urllib.request.Request(u, headers=HDR)
        with urllib.request.urlopen(req, timeout=40) as r, open(path, "wb") as f:
            f.write(r.read())
        im = Image.open(path)
        print(f"--- img {i}: {path} size={im.size} ---")
        # 分块 OCR：长图按 2000px 高度切片
        w, h = im.size
        tile = 2000
        y = 0
        while y < h:
            crop = im.crop((0, y, w, min(y + tile, h)))
            res, _ = engine(np.array(crop.convert("RGB")))
            if res:
                for box, text, score in res:
                    t = text.strip()
                    if t:
                        print(f"[{y:>5}] {t}")
            y += tile


if __name__ == "__main__":
    main()
