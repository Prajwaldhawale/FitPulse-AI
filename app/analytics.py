from typing import Any


def calculate_bmi(height_cm: float, weight_kg: float) -> dict[str, Any]:
    """Calculate Body Mass Index (BMI) and health categorization."""
    if height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Height and weight must be positive numbers")

    height_m = height_cm / 100.0
    bmi = round(weight_kg / (height_m ** 2), 1)

    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25.0:
        category = "Normal weight"
    elif bmi < 30.0:
        category = "Overweight"
    else:
        category = "Obese"

    min_healthy = round(18.5 * (height_m ** 2), 1)
    max_healthy = round(24.9 * (height_m ** 2), 1)

    return {
        "bmi": bmi,
        "category": category,
        "healthy_weight_range_kg": [min_healthy, max_healthy],
    }


def calculate_one_rep_max(weight_kg: float, reps: int) -> float:
    """Calculate estimated 1-Rep Max using the Epley formula."""
    if weight_kg < 0 or reps <= 0:
        raise ValueError("Weight must be non-negative and reps must be at least 1")

    if reps == 1:
        return round(weight_kg, 1)

    # Epley formula: 1RM = weight * (1 + reps / 30)
    one_rm = weight_kg * (1.0 + (reps / 30.0))
    return round(one_rm, 1)


def detect_progressive_overload(
    exercise_name: str,
    weight_kg: float,
    reps: int,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Compare current set against prior logged session for the same exercise.
    Returns whether progressive overload was achieved, overload delta, and badges.
    """
    past_sets = [
        s for s in history if s.get("exercise_name", "").lower() == exercise_name.lower()
    ]

    current_1rm = calculate_one_rep_max(weight_kg, reps)
    current_volume = weight_kg * reps

    if not past_sets:
        return {
            "is_overload": True,
            "badge": "🎯 Baseline Set",
            "delta_type": "baseline",
            "message": f"First recorded session for {exercise_name}. Baseline established!",
            "estimated_1rm": current_1rm,
        }

    # Best prior set by 1RM
    best_prior_weight = max(s.get("weight_kg", 0) for s in past_sets)
    best_prior_volume = max(s.get("weight_kg", 0) * s.get("reps", 0) for s in past_sets)
    best_prior_1rm = max(
        calculate_one_rep_max(s.get("weight_kg", 0), s.get("reps", 1)) for s in past_sets
    )

    if weight_kg > best_prior_weight:
        diff = round(weight_kg - best_prior_weight, 1)
        return {
            "is_overload": True,
            "badge": f"🔥 +{diff}kg Weight PR",
            "delta_type": "weight",
            "message": f"New weight record! Lifted +{diff}kg heavier than prior best.",
            "estimated_1rm": current_1rm,
        }
    elif current_volume > best_prior_volume:
        vol_pct = round(((current_volume - best_prior_volume) / best_prior_volume) * 100, 1)
        return {
            "is_overload": True,
            "badge": f"⚡ +{vol_pct}% Volume",
            "delta_type": "volume",
            "message": f"Volume overload achieved (+{vol_pct}% work capacity).",
            "estimated_1rm": current_1rm,
        }
    elif current_1rm > best_prior_1rm:
        diff_1rm = round(current_1rm - best_prior_1rm, 1)
        return {
            "is_overload": True,
            "badge": f"📈 +{diff_1rm}kg 1RM",
            "delta_type": "1rm",
            "message": f"Estimated strength capacity increased by {diff_1rm}kg.",
            "estimated_1rm": current_1rm,
        }
    else:
        return {
            "is_overload": False,
            "badge": "✓ Consistent Volume",
            "delta_type": "maintenance",
            "message": "Solid volume maintenance set.",
            "estimated_1rm": current_1rm,
        }


def calculate_recovery_score(
    sleep_hours: float,
    water_liters: float,
    protein_grams: float,
    target_protein: float = 160.0,
) -> dict[str, Any]:
    """Calculate a 0-100 recovery score based on sleep, hydration, and nutrition."""
    # Sleep: 8 hours = 40 points
    sleep_score = min(40.0, (sleep_hours / 8.0) * 40.0)

    # Protein: Target = 40 points
    protein_score = min(40.0, (protein_grams / max(1.0, target_protein)) * 40.0)

    # Water: 3.5 Liters = 20 points
    water_score = min(20.0, (water_liters / 3.5) * 20.0)

    total_score = round(sleep_score + protein_score + water_score)
    total_score = min(100, max(0, total_score))

    if total_score >= 85:
        readiness = "Prime Readiness"
        advice = "Body is fully recovered and primed for heavy progressive overload."
    elif total_score >= 65:
        readiness = "Moderate Recovery"
        advice = "Adequate recovery. Hydrate and warm up thoroughly before heavy sets."
    else:
        readiness = "Low Recovery"
        advice = "Recovery deficit detected. Prioritize sleep and protein today to prevent fatigue."

    return {
        "score": total_score,
        "readiness": readiness,
        "advice": advice,
        "components": {
            "sleep_pts": round(sleep_score, 1),
            "protein_pts": round(protein_score, 1),
            "water_pts": round(water_score, 1),
        },
    }
