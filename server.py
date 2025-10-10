from fastapi import FastAPI, Query, HTTPException
from datetime import datetime, timedelta
import os, pytz, httpx

app = FastAPI()

HK_TZ = pytz.timezone("Asia/Hong_Kong")
CAL_API_KEY = os.environ.get("CAL_API_KEY")  # set via export CAL_API_KEY=cal_live_...
SCHEDULE_ID = "964634"

WEEKDAY_NUM_TO_NAME = {
    1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday",
    5: "Friday", 6: "Saturday", 7: "Sunday"
}

@app.get("/")
def root():
    return {"status": "ok", "paths": ["/time/hk", "/open/hk"]}

@app.get("/time/hk")
def time_hk():
    now = datetime.now(HK_TZ)
    return {"datetime": now.isoformat(), "weekdayNum": now.isoweekday(), "timezone": "Asia/Hong_Kong"}

def to_hk_date(date_str: str | None, offset_days: int | None) -> datetime:
    now_hk = datetime.now(HK_TZ)
    if date_str:
        return HK_TZ.localize(datetime.strptime(date_str, "%Y-%m-%d"))
    if offset_days is not None:
        return (now_hk + timedelta(days=offset_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return now_hk.replace(hour=0, minute=0, second=0, microsecond=0)

def pick_hours(payload: dict, target_date_hk: datetime):
    data = payload.get("data", {})
    overrides = data.get("overrides", []) or []
    availability = data.get("availability", []) or []

    target_date_str = target_date_hk.strftime("%Y-%m-%d")
    for ov in overrides:
        if ov.get("date") == target_date_str:
            return True, ov.get("startTime"), ov.get("endTime"), data.get("timeZone", "Asia/Hong_Kong")

    weekday_name = WEEKDAY_NUM_TO_NAME[target_date_hk.isoweekday()]
    for block in availability:
        if weekday_name in (block.get("days") or []):
            return True, block.get("startTime"), block.get("endTime"), data.get("timeZone", "Asia/Hong_Kong")

    return False, None, None, data.get("timeZone", "Asia/Hong_Kong")

@app.get("/open/hk")
async def open_for_date(
    date: str | None = Query(default=None, description="YYYY-MM-DD in Asia/Hong_Kong"),
    offsetDays: int | None = Query(default=None, description="0=today, 1=tomorrow, 2=day after")
):
    if not CAL_API_KEY:
        raise HTTPException(status_code=500, detail="Missing CAL_API_KEY")

    target_date_hk = to_hk_date(date, offsetDays)
    headers = {"Authorization": f"Bearer {CAL_API_KEY}", "cal-api-version": "2024-06-11"}
    url = f"https://api.cal.com/v2/schedules/{SCHEDULE_ID}"

    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        payload = r.json()

    is_open, start, end, tz = pick_hours(payload, target_date_hk)
    return {
        "date": target_date_hk.strftime("%Y-%m-%d"),
        "weekday": WEEKDAY_NUM_TO_NAME[target_date_hk.isoweekday()],
        "timezone": tz,
        "open": is_open,
        "start": start,
        "end": end
    }
