import requests, json, time, sys, pathlib, os
from datetime import datetime

SITE, MOVIE, SCREEN = "0257", "오디세이", "IMAX"
BASE = "https://cgv.co.kr/api/v1/booking"
HEAD = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://cgv.co.kr/cnm/movieBook/cinema",
    "Origin": "https://cgv.co.kr",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}
STATE = pathlib.Path("cgv_state.json")
TOKEN = os.environ.get("TG_TOKEN", "")
CHAT  = os.environ.get("TG_CHAT", "")
INTERVAL = 300

def api(path, **p):
    p["coCd"] = "A420"
    r = requests.get(f"{BASE}/{path}", params=p, headers=HEAD, timeout=15)
    r.raise_for_status()
    return r.json().get("data") or []

def scan():
    found = {}
    for d in api("searchSiteScnscYmdListBySite", siteNo=SITE):
        ymd = d["scnYmd"]
        for s in api("searchMovScnInfo", siteNo=SITE, scnYmd=ymd, rtctlScopCd="08"):
            if MOVIE in (s.get("movNm") or "") and SCREEN in (s.get("scnsEnm") or ""):
                t = s["scnsrtTm"]
                found.setdefault(ymd, []).append(
                    f"{t[:2]}:{t[2:]} ({s['frSeatCnt']}/{s['stcnt']}석)")
        time.sleep(0.5)
    return found

def notify(msg):
    print(msg)
    if TOKEN and CHAT:
        try:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                          json={"chat_id": CHAT, "text": msg}, timeout=15)
        except Exception as e:
            print("텔레그램 실패:", e)

def check():
    known = set(json.loads(STATE.read_text())) if STATE.exists() else None
    try:
        found = scan()
    except Exception as e:
        print(f"[{datetime.now():%H:%M}] 조회 실패: {e}")
        return
    cur = set(found)

    if known is None:
        print(f"[{datetime.now():%H:%M}] 최초 기록 — 현재 {len(cur)}일")
        for d in sorted(found):
            print(f"  {d}: {', '.join(found[d])}")
    else:
        new = cur - known
        if new:
            lines = [f"{d}\n  " + "\n  ".join(found[d]) for d in sorted(new)]
            notify("🎬 광교 IMAX 오디세이 새 날짜!\n\n" + "\n\n".join(lines)
                   + "\n\nhttps://cgv.co.kr/cnm/movieBook/cinema")
        else:
            print(f"[{datetime.now():%H:%M}] 변동 없음 ({len(cur)}일)")

    STATE.write_text(json.dumps(sorted(cur | (known or set()))))

if __name__ == "__main__":
    if "--once" in sys.argv:
        check()
    else:
        print(f"감시 시작 ({INTERVAL}초 간격). Ctrl+C로 중단.")
        while True:
            check()
            time.sleep(INTERVAL)
