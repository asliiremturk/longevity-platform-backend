-- Longevity and Healthy Aging Platform - Veritabanı Şeması
-- Proje 6 - YBS437

-- Kullanıcı profili
CREATE TABLE users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    age           INTEGER NOT NULL,
    gender        TEXT CHECK(gender IN ('M', 'F', 'other')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Günlük izlenen veri alanları (en az 4: uyku, adım, egzersiz, beslenme)
CREATE TABLE daily_metrics (
    metric_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    date          TEXT NOT NULL,              -- 'YYYY-MM-DD'
    sleep_hours   REAL,
    steps         INTEGER,
    exercise_min  INTEGER,
    nutrition_score REAL,                     -- 0-100 arası basit bir skor
    resting_hr    INTEGER,                    -- opsiyonel 5. alan
    UNIQUE(user_id, date)
);

-- Kişiselleştirilmiş hedefler
CREATE TABLE goals (
    goal_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    metric_name   TEXT NOT NULL,              -- 'steps', 'sleep_hours' vb.
    target_value  REAL NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    status        TEXT DEFAULT 'active'       -- 'active' | 'achieved' | 'revised'
);

-- Tespit edilen anomaliler (negatif/olağan dışı değişiklikler)
CREATE TABLE anomalies (
    anomaly_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    date          TEXT NOT NULL,
    metric_name   TEXT NOT NULL,
    description   TEXT,
    severity      TEXT CHECK(severity IN ('low', 'medium', 'high')),
    review_status TEXT DEFAULT 'pending'       -- 'pending' | 'reviewed' | 'dismissed'
);

-- Haftalık ilerleme raporları
CREATE TABLE weekly_reports (
    report_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    week_start    TEXT NOT NULL,
    trend_summary TEXT,                        -- model çıktısının metne dönüşmüş hali
    mae_sleep     REAL,                         -- o haftaki tahmin hatası (opsiyonel, izleme için)
    mae_steps     REAL,
    generated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
