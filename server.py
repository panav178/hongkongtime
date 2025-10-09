from fastapi import FastAPI
from datetime import datetime
import pytz

app = FastAPI()

@app.get("/time/hk")
def time_hk():
    tz = pytz.timezone("Asia/Hong_Kong")
    now = datetime.now(tz)
    return {
        "datetime": now.isoformat(),
        "weekdayNum": now.isoweekday(),  # 1=Mon ... 7=Sun
        "timezone": "Asia/Hong_Kong",
    }