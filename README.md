# Longevity Platform – Backend API

YBS437 · Project 6 · Team 8 — AI-Powered Longevity and Healthy Aging Platform.

FastAPI + SQLite backend. It stores daily health metrics, runs the AI component
through one function (`predict.py`) and records user feedback on alerts.

## What works now
- Create users and save daily metrics (sleep, steps, exercise, nutrition, resting heart rate).
- `GET /predict/{user_id}`: next-day forecast and an alert if the latest day is unusually bad for that user.
- `POST /anomalies/{anomaly_id}/feedback`: the user marks an alert as useful or a false alarm.
- `GET /feedback-summary`: counts of useful alerts, false alarms and the false-alarm rate (input for error analysis).

## What is a placeholder
The AI component in `predict.py` is currently the Milestone 2 baseline
(personal z-score vs. the user's previous 28 days, threshold 2.0).
The trained model will replace the inside of `predict()` only; the API does not change.

## Model contract
`predict(history: list[dict]) -> dict`
- `history`: one user's daily rows, oldest first (`date`, `sleep_hours`, `steps`, `exercise_min`, `nutrition_score`, `resting_hr`).
- returns: `model`, `forecast`, `alert`, `anomalies`, `reason`.

## Run it
```
pip install -r requirements.txt
python -m uvicorn main:app --reload
```
Open http://127.0.0.1:8000/docs for the test page.

To load demo data (two users, one with a bad last day), run in a second terminal:
```
python seed.py
```

## Data note
All data is synthetic. Results on synthetic data are not real-world accuracy.
