import os
from datetime import datetime, timezone
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.database import get_connection, init_db
from app.analytics import (
    calculate_bmi,
    calculate_one_rep_max,
    detect_progressive_overload,
    calculate_recovery_score,
)
from app.ai_coach import get_ai_trainer_advice

init_db()

app = FastAPI(title="FitPulse AI - Fitness & Hypertrophy Tracker", version="1.0.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health():
    return {"status": "healthy", "service": "FitPulse-AI", "version": "1.0.0"}


class WorkoutCreate(BaseModel):
    exercise_name: str = Field(min_length=1)
    muscle_group: str = Field(default="Chest")
    weight_kg: float = Field(gt=0)
    reps: int = Field(gt=0)


class MetricsCreate(BaseModel):
    height_cm: float = Field(gt=50, lt=280)
    weight_kg: float = Field(gt=20, lt=350)


class HabitsCreate(BaseModel):
    protein_grams: float = Field(ge=0)
    water_liters: float = Field(ge=0)
    sleep_hours: float = Field(ge=0, le=24)


@app.get("/api/dashboard")
def get_dashboard():
    conn = get_connection()
    c = conn.cursor()

    # Latest body metrics
    c.execute("SELECT * FROM body_metrics ORDER BY id DESC LIMIT 1;")
    metric_row = c.fetchone()
    metrics = dict(metric_row) if metric_row else {
        "height_cm": 175.0, "weight_kg": 72.0, "bmi": 23.5, "bmi_category": "Normal weight"
    }

    # Latest daily habits
    c.execute("SELECT * FROM daily_habits ORDER BY id DESC LIMIT 1;")
    habit_row = c.fetchone()
    habits = dict(habit_row) if habit_row else {
        "protein_grams": 130.0, "water_liters": 2.5, "sleep_hours": 7.0, "recovery_score": 75
    }

    # Recent workouts
    c.execute("SELECT * FROM workouts ORDER BY id DESC LIMIT 15;")
    workouts = [dict(row) for row in c.fetchall()]

    conn.close()

    total_volume = sum(w["weight_kg"] * w["reps"] for w in workouts)
    overload_sets = sum(1 for w in workouts if w["is_overload"])

    return {
        "metrics": metrics,
        "habits": habits,
        "workouts": workouts,
        "summary": {
            "total_logged_sets": len(workouts),
            "overload_sets": overload_sets,
            "total_volume_kg": round(total_volume, 1),
        }
    }


@app.post("/api/workouts", status_code=201)
def log_workout(item: WorkoutCreate):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT exercise_name, weight_kg, reps FROM workouts;")
    history = [dict(row) for row in c.fetchall()]

    overload_info = detect_progressive_overload(
        item.exercise_name, item.weight_kg, item.reps, history
    )

    one_rm = overload_info["estimated_1rm"]
    is_overload = overload_info["is_overload"]
    badge = overload_info["badge"]
    now = datetime.now(timezone.utc).isoformat()

    c.execute("""
    INSERT INTO workouts (exercise_name, muscle_group, weight_kg, reps, estimated_1rm, is_overload, overload_badge, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (item.exercise_name, item.muscle_group, item.weight_kg, item.reps, one_rm, is_overload, badge, now))

    new_id = c.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": new_id,
        "exercise_name": item.exercise_name,
        "muscle_group": item.muscle_group,
        "weight_kg": item.weight_kg,
        "reps": item.reps,
        "estimated_1rm": one_rm,
        "is_overload": is_overload,
        "overload_badge": badge,
        "message": overload_info["message"],
        "created_at": now,
    }


@app.post("/api/metrics", status_code=201)
def update_metrics(item: MetricsCreate):
    bmi_info = calculate_bmi(item.height_cm, item.weight_kg)
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO body_metrics (height_cm, weight_kg, bmi, bmi_category, created_at)
    VALUES (?, ?, ?, ?, ?);
    """, (item.height_cm, item.weight_kg, bmi_info["bmi"], bmi_info["category"], now))
    conn.commit()
    conn.close()

    return {
        "height_cm": item.height_cm,
        "weight_kg": item.weight_kg,
        "bmi": bmi_info["bmi"],
        "bmi_category": bmi_info["category"],
        "healthy_weight_range_kg": bmi_info["healthy_weight_range_kg"],
    }


@app.post("/api/habits", status_code=201)
def update_habits(item: HabitsCreate):
    recovery = calculate_recovery_score(item.sleep_hours, item.water_liters, item.protein_grams)
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO daily_habits (protein_grams, water_liters, sleep_hours, recovery_score, created_at)
    VALUES (?, ?, ?, ?, ?);
    """, (item.protein_grams, item.water_liters, item.sleep_hours, recovery["score"], now))
    conn.commit()
    conn.close()

    return {
        "protein_grams": item.protein_grams,
        "water_liters": item.water_liters,
        "sleep_hours": item.sleep_hours,
        "recovery_score": recovery["score"],
        "readiness": recovery["readiness"],
        "advice": recovery["advice"],
    }


@app.post("/api/ai-coach")
def consult_ai_coach():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM workouts ORDER BY id DESC LIMIT 10;")
    workouts = [dict(row) for row in c.fetchall()]

    c.execute("SELECT * FROM body_metrics ORDER BY id DESC LIMIT 1;")
    m_row = c.fetchone()
    metrics = dict(m_row) if m_row else {}

    c.execute("SELECT * FROM daily_habits ORDER BY id DESC LIMIT 1;")
    h_row = c.fetchone()
    habits = dict(h_row) if h_row else {}
    conn.close()

    advice = get_ai_trainer_advice(workouts, habits, metrics)
    return advice
