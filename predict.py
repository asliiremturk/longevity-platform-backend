"""
Model <-> API sözleşmesi (contract).

API, modelden SADECE bu fonksiyonu çağırır:

    predict(history: list[dict]) -> dict

history : Bir kullanıcının günlük verisi, tarihe göre eskiden yeniye sıralı.
          Her satır: {"date": "YYYY-MM-DD", "sleep_hours": 7.1, "steps": 8000,
                      "exercise_min": 20, "nutrition_score": 60, "resting_hr": 64}
          Eksik değer None olabilir.

Dönen sözlük (model değişse de bu şekil DEĞİŞMEZ):
    {
      "model":    "baseline_zscore_v0",
      "forecast": {"sleep_hours": 7.0, "steps": 8000.0},   # yarın için tahmin (veya None)
      "alert":    True/False,                              # son gün için uyarı var mı
      "anomalies": [ {"date", "metric_name", "severity", "description"} ],
      "reason":   "kısa açıklama"
    }

Şimdilik içinde M2'deki baseline var (kişisel z-skoru). Yiğit'in modeli
hazır olunca SADECE bu dosyanın içi değişir; main.py'ye dokunulmaz.
"""

from statistics import mean, pstdev

MODEL_NAME = "baseline_zscore_v0"
WINDOW = 28          # kişisel geçmiş penceresi (gün)
MIN_VALID = 14       # pencerede en az bu kadar dolu gün yoksa uyarı verme
Z_THRESHOLD = 2.0    # M2 baseline eşiği

# Hangi yönde sapma "kötü" sayılır: -1 = düşüş kötü, +1 = artış kötü
BAD_DIRECTION = {"sleep_hours": -1, "steps": -1, "resting_hr": +1}


def _values(history, key):
    return [r.get(key) for r in history]


def _forecast(history) -> dict:
    """Yarın için tahmin: son 7 günün ortalaması (7 günlük hareketli ortalama baseline'ı)."""
    out = {}
    for key in ("sleep_hours", "steps"):
        last7 = [v for v in _values(history[-7:], key) if v is not None]
        out[key] = round(mean(last7), 2) if len(last7) >= 4 else None
    return out


def _severity(z: float) -> str:
    z = abs(z)
    return "high" if z >= 3 else "medium" if z >= 2.5 else "low"


def _check_last_day(history) -> list:
    """Son günü, kullanıcının önceki 28 günüyle karşılaştırır."""
    if len(history) < 2:
        return []
    today = history[-1]
    past = history[-(WINDOW + 1):-1]
    found = []
    for key, direction in BAD_DIRECTION.items():
        x = today.get(key)
        base = [v for v in _values(past, key) if v is not None]
        if x is None or len(base) < MIN_VALID:
            continue
        sd = pstdev(base)
        if sd == 0:
            continue
        z = (x - mean(base)) / sd
        if z * direction >= Z_THRESHOLD:
            found.append({
                "date": today["date"],
                "metric_name": key,
                "severity": _severity(z),
                "description": f"{key} kişisel ortalamadan {abs(z):.1f} standart sapma "
                               f"{'düşük' if direction < 0 else 'yüksek'}",
            })
    return found


def predict(history: list) -> dict:
    if not history:
        return {"model": MODEL_NAME, "forecast": {"sleep_hours": None, "steps": None},
                "alert": False, "anomalies": [], "reason": "Veri yok"}
    anomalies = _check_last_day(history)
    return {
        "model": MODEL_NAME,
        "forecast": _forecast(history),
        "alert": bool(anomalies),
        "anomalies": anomalies,
        "reason": ("Son gün kişisel düzeyden olumsuz sapıyor" if anomalies
                   else "Son gün kişisel aralığın içinde veya yeterli geçmiş yok"),
    }
