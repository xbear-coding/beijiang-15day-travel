# -*- coding: utf-8 -*-
"""GitHub Actions 定时抓取天气快照 → assets/weather.json（同域静态数据）。
页面优先读这个文件，彻底避开浏览器跨域/跨境请求；抓取失败时不覆盖旧快照。
r122：除最高/最低温外，同时取 WMO weathercode（页面据此显示阴晴雨雪/雾），
      否则每小时定时任务会用「只有温度」的旧结构把天气现象覆盖掉。
"""
import io, json, os, sys, time, datetime, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "assets", "weather.json")

POINTS = [
    ("乌鲁木齐", 43.876, 87.615),
    ("阿勒泰", 47.827, 88.133),
    ("禾木", 48.578, 87.441),
    ("喀纳斯", 48.786, 87.057),
    ("白哈巴", 48.6935, 86.7839),
    ("布尔津", 47.694, 86.874),
    ("乌尔禾", 46.091, 85.697),
    ("独山子", 44.329, 84.887),
    ("赛里木湖", 44.609, 81.119),
    ("温泉县", 44.981, 81.036),
]


def build_url():
    lat = ",".join("%.4f" % p[1] for p in POINTS)
    lon = ",".join("%.4f" % p[2] for p in POINTS)
    return ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
            "&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=Asia/Shanghai&forecast_days=1"
            % (lat, lon))


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "beijiang-roadbook/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:      # noqa: BLE001
            last = e
            print("第 %d 次失败：%s" % (i + 1, e))
            time.sleep(3)
    raise last


def main():
    try:
        raw = fetch(build_url())
    except Exception as e:          # noqa: BLE001
        print("抓取失败，保留旧快照：%s" % e)
        return 0

    items = raw if isinstance(raw, list) else [raw]
    pts = []
    for i, (name, la, lo) in enumerate(POINTS):
        d = items[i].get("daily", {}) if i < len(items) else {}
        tmax = (d.get("temperature_2m_max") or [None])[0]
        tmin = (d.get("temperature_2m_min") or [None])[0]
        # WMO 天气码：Open-Meteo 的 daily 数组键名是 weathercode（兼容 weather_code 写法）
        wcode = (d.get("weathercode") or d.get("weather_code") or [None])[0]
        pts.append({
            "loc": name, "lat": la, "lon": lo,
            "date": (d.get("time") or [None])[0],
            "tmin": None if tmin is None else round(tmin),
            "tmax": None if tmax is None else round(tmax),
            "code": None if wcode is None else int(wcode),
        })

    if not any(p["tmin"] is not None for p in pts):
        print("返回无有效温度，保留旧快照")
        return 0

    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    payload = {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "generated_cn": now.strftime("%Y-%m-%d %H:%M"),
        "source": "open-meteo",
        "source_url": "https://open-meteo.com/",
        "license": "CC-BY-4.0",
        "points": pts,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("写入 %s，生成时间 %s" % (OUT, payload["generated_cn"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
