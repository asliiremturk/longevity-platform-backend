"""
Longevity and Healthy Aging Platform - Backend API
Proje 6 - YBS437
Application and Integration Developer başlangıç iskeleti

Çalıştırmak için:
    pip install -r requirements.txt
    uvicorn main:app --reload

Sonra tarayıcıda http://127.0.0.1:8000/docs -> otomatik oluşan test arayüzü
"""

import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from predict import predict  # model <-> API sözleşmesi (bkz. predict.py)

DB_PATH = Path(__file__).parent / "longevity.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

app = FastAPI(title="Longevity Platform API")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.on_event("startup")
def init_db():
    """Veritabanı yoksa şemadan oluştur (LBYL: önce kontrol et)."""
    if not DB_PATH.exists():
        conn = get_connection()
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()


# ---------- Pydantic modelleri (gelen/giden veri şekli) ----------

class DailyMetricIn(BaseModel):
    user_id: int
    date: str          # "YYYY-MM-DD"
    sleep_hours: Optional[float] = None
    steps: Optional[int] = None
    exercise_min: Optional[int] = None
    nutrition_score: Optional[float] = None
    resting_hr: Optional[int] = None


class UserIn(BaseModel):
    age: int
    gender: Optional[str] = None   # 'M' | 'F' | 'other'


# ---------- Uç noktalar ----------

@app.post("/users")
def create_user(user: UserIn):
    """Yeni bir kullanıcı oluşturur ve user_id'sini döndürür."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO users (age, gender) VALUES (?, ?)",
        (user.age, user.gender),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"user_id": new_id, "age": user.age, "gender": user.gender}


@app.post("/metrics")
def add_metric(metric: DailyMetricIn):
    """Günlük veriyi kaydeder. LBYL: kaydetmeden önce kullanıcı var mı kontrol edilir."""
    conn = get_connection()
    user_exists = conn.execute(
        "SELECT 1 FROM users WHERE user_id = ?", (metric.user_id,)
    ).fetchone()
    if not user_exists:
        conn.close()
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    conn.execute(
        """INSERT OR REPLACE INTO daily_metrics
           (user_id, date, sleep_hours, steps, exercise_min, nutrition_score, resting_hr)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (metric.user_id, metric.date, metric.sleep_hours, metric.steps,
         metric.exercise_min, metric.nutrition_score, metric.resting_hr),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


def load_history(user_id: int):
    """Kullanıcının tüm günlük verisini eskiden yeniye sıralı liste olarak döndürür."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT date, sleep_hours, steps, exercise_min, nutrition_score, resting_hr
           FROM daily_metrics WHERE user_id = ? ORDER BY date ASC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/trends/{user_id}")
def get_trends(user_id: int):
    """Yarın için tahmin. Hesabı predict.py yapar; model değişince burası değişmez."""
    history = load_history(user_id)
    if not history:
        raise HTTPException(status_code=404, detail="Veri bulunamadı")
    result = predict(history)
    return {"user_id": user_id, "forecast": result["forecast"], "method": result["model"]}


@app.get("/predict/{user_id}")
def get_prediction(user_id: int):
    """
    Tek çağrıda tahmin + uyarı. Uyarı varsa anomalies tablosuna kaydeder
    (aynı gün ve metrik için tekrar kaydetmez).
    """
    history = load_history(user_id)
    if not history:
        raise HTTPException(status_code=404, detail="Veri bulunamadı")
    result = predict(history)

    conn = get_connection()
    for a in result["anomalies"]:
        exists = conn.execute(
            "SELECT 1 FROM anomalies WHERE user_id=? AND date=? AND metric_name=?",
            (user_id, a["date"], a["metric_name"]),
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO anomalies (user_id, date, metric_name, description, severity) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, a["date"], a["metric_name"], a["description"], a["severity"]),
            )
    conn.commit()
    conn.close()
    return {"user_id": user_id, **result}


@app.get("/anomalies/{user_id}")
def get_anomalies(user_id: int):
    """Kullanıcı için kaydedilmiş anomalileri döndürür."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM anomalies WHERE user_id = ? ORDER BY date DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


class FeedbackIn(BaseModel):
    useful: bool   # True = "Faydalı", False = "Yanlış alarm"


@app.post("/anomalies/{anomaly_id}/feedback")
def give_feedback(anomaly_id: int, feedback: FeedbackIn):
    """
    Kullanıcının uyarıya cevabını kaydeder.
    Faydalı      -> review_status = 'reviewed'
    Yanlış alarm -> review_status = 'dismissed'
    Bu cevaplar M4'teki hata analizinin (yanlış alarm oranı) kaynağıdır.
    """
    status = "reviewed" if feedback.useful else "dismissed"
    conn = get_connection()
    exists = conn.execute(
        "SELECT 1 FROM anomalies WHERE anomaly_id = ?", (anomaly_id,)
    ).fetchone()
    if not exists:
        conn.close()
        raise HTTPException(status_code=404, detail="Uyarı bulunamadı")
    conn.execute(
        "UPDATE anomalies SET review_status = ? WHERE anomaly_id = ?",
        (status, anomaly_id),
    )
    conn.commit()
    conn.close()
    return {"anomaly_id": anomaly_id, "review_status": status}


@app.get("/feedback-summary")
def feedback_summary():
    """Kaç uyarı faydalı, kaç yanlış alarm, kaçı henüz cevaplanmadı."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT review_status, COUNT(*) AS n FROM anomalies GROUP BY review_status"
    ).fetchall()
    conn.close()
    counts = {r["review_status"]: r["n"] for r in rows}
    useful = counts.get("reviewed", 0)
    false_alarm = counts.get("dismissed", 0)
    answered = useful + false_alarm
    return {
        "useful": useful,
        "false_alarm": false_alarm,
        "pending": counts.get("pending", 0),
        "false_alarm_rate": round(false_alarm / answered, 3) if answered else None,
    }


@app.get("/weekly-report/{user_id}")
def get_weekly_report(user_id: int):
    """En güncel haftalık raporu döndürür."""
    conn = get_connection()
    row = conn.execute(
        """SELECT * FROM weekly_reports WHERE user_id = ?
           ORDER BY week_start DESC LIMIT 1""",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Henüz rapor oluşturulmamış")
    return dict(row)


@app.get("/")
def root():
    return {"message": "Longevity Platform API çalışıyor. /docs adresine bakabilirsiniz."}
