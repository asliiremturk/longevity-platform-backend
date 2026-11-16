"""
Deneme verisi yükler ve /predict'i çağırır.
API açıkken (uvicorn çalışırken) ayrı bir terminalde çalıştır:  python seed.py

Ne yapar?
  1) İki kullanıcı oluşturur.
  2) Her birine 30 günlük veri yükler.
       - Kullanıcı A: 30 gün normal.
       - Kullanıcı B: 29 gün normal, SON GÜN kötü (uyku 3 saat, nabız 92).
  3) Her kullanıcı için /predict çağırır ve sonucu yazdırır.
Beklenen: A için alert=False, B için alert=True.
"""
import json
import urllib.request
from datetime import date, timedelta

BASE = "http://127.0.0.1:8000"


def call(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))


def make_user(age, gender):
    return call("POST", "/users", {"age": age, "gender": gender})["user_id"]


def load_days(user_id, bad_last_day):
    start = date(2026, 10, 1)
    for i in range(30):
        sleep = 7.0 + (0.3 if i % 2 else -0.3)       # 6.7 / 7.3 arasında gidip gelir
        steps = 8000 + (i % 5) * 200
        hr = 64 + (1 if i % 3 == 0 else 0)
        if bad_last_day and i == 29:
            sleep, hr = 3.0, 92                       # kötü son gün
        call("POST", "/metrics", {
            "user_id": user_id,
            "date": str(start + timedelta(days=i)),
            "sleep_hours": sleep,
            "steps": steps,
            "exercise_min": 20,
            "nutrition_score": 60,
            "resting_hr": hr,
        })


for name, bad in (("Kullanıcı A (normal)", False), ("Kullanıcı B (son gün kötü)", True)):
    uid = make_user(55, "F")
    load_days(uid, bad)
    result = call("GET", f"/predict/{uid}")
    print("=" * 60)
    print(name, "-> user_id:", uid)
    print("alert   :", result["alert"])
    print("forecast:", result["forecast"])
    print("neden   :", result["reason"])
    for a in result["anomalies"]:
        print("  uyarı :", a["metric_name"], "|", a["severity"], "|", a["description"])
print("=" * 60)
print("Bitti. Tarayıcıda /docs ekranından /predict/{user_id} ile de deneyebilirsin.")
