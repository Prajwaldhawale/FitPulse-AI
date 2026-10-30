import sqlite3
import os
from datetime import datetime, timezone
from typing import Any

DB_PATH = os.getenv("SQLITE_DB_PATH", "fitpulse.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exercise_name TEXT NOT NULL,
        muscle_group TEXT NOT NULL,
        weight_kg REAL NOT NULL,
        reps INTEGER NOT NULL,
        estimated_1rm REAL NOT NULL,
        is_overload BOOLEAN NOT NULL,
        overload_badge TEXT,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS body_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        height_cm REAL NOT NULL,
        weight_kg REAL NOT NULL,
        bmi REAL NOT NULL,
        bmi_category TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        protein_grams REAL NOT NULL,
        water_liters REAL NOT NULL,
        sleep_hours REAL NOT NULL,
        recovery_score INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # Check if seed data exists
    cursor.execute("SELECT COUNT(*) FROM workouts;")
    if cursor.fetchone()[0] == 0:
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
        INSERT INTO body_metrics (height_cm, weight_kg, bmi, bmi_category, created_at)
        VALUES (178.0, 75.5, 23.8, 'Normal weight', ?)
        """, (now,))

        cursor.execute("""
        INSERT INTO daily_habits (protein_grams, water_liters, sleep_hours, recovery_score, created_at)
        VALUES (150.0, 3.2, 7.5, 88, ?)
        """, (now,))

        cursor.execute("""
        INSERT INTO workouts (exercise_name, muscle_group, weight_kg, reps, estimated_1rm, is_overload, overload_badge, created_at)
        VALUES 
        ('Barbell Bench Press', 'Chest', 80.0, 8, 101.3, 1, '🎯 Baseline Set', ?),
        ('Incline Dumbbell Press', 'Chest', 32.0, 10, 42.7, 1, '🎯 Baseline Set', ?),
        ('Barbell Back Squat', 'Legs', 100.0, 6, 120.0, 1, '🎯 Baseline Set', ?)
        """, (now, now, now))

    conn.commit()
    conn.close()
