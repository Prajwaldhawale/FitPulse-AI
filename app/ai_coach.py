import json
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

COACH_SYSTEM_PROMPT = """
You are Coach Iron, an elite sports scientist, strength & conditioning coach, and hypertrophy expert.
Your job is to analyze the athlete's workout performance, progressive overload trends, and daily recovery (protein, water, sleep, BMI).

Guidelines:
1. Praise progressive overload breakthroughs specifically (mention weights, reps, or volume).
2. If recovery (sleep < 7 hrs or protein < 1.6g/kg) is lacking, explicitly explain how it limits muscle growth.
3. Provide 2-3 specific, actionable recommendations for the athlete's next session.
4. Keep the tone motivational, scientific, energetic, and concise.

Return valid JSON with:
{
  "coach_headline": "Punchy 1-line motivational takeaway",
  "overload_analysis": "Assessment of progressive overload achievements",
  "recovery_analysis": "Assessment of sleep, hydration, protein, and BMI",
  "recommendations": ["Actionable step 1", "Actionable step 2"],
  "focus_muscle_group": "Target muscle for next session"
}
"""


def get_ai_trainer_advice(
    workout_history: list[dict[str, Any]],
    recovery_stats: dict[str, Any],
    body_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Generate personalized trainer feedback using Amazon Bedrock with heuristic fallback."""
    region = os.getenv("AWS_REGION", "us-east-1")
    model_id = os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")

    context_payload = {
        "recent_workouts": workout_history[-10:],
        "recovery": recovery_stats,
        "body_metrics": body_metrics,
    }

    try:
        client = boto3.client("bedrock-runtime", region_name=region)
        response = client.converse(
            modelId=model_id,
            system=[{"text": COACH_SYSTEM_PROMPT}],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": (
                                "Analyze this athlete's data and return the JSON coaching analysis:\n\n"
                                + json.dumps(context_payload, default=str)
                            )
                        }
                    ],
                }
            ],
            inferenceConfig={"maxTokens": 800, "temperature": 0.3},
        )

        content = response["output"]["message"]["content"]
        raw_text = "\n".join(item["text"] for item in content if "text" in item).strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

        result = json.loads(raw_text)
        result["engine"] = f"Bedrock ({model_id})"
        return result

    except Exception as e:
        logger.warning(f"Bedrock coach invocation failed ({e}), using sports science fallback")

    # Heuristic Intelligent Sports Science Coach Fallback
    sleep = recovery_stats.get("sleep_hours", 7.0)
    protein = recovery_stats.get("protein_grams", 130.0)
    bmi = body_metrics.get("bmi", 23.0)

    overload_count = sum(1 for w in workout_history if w.get("is_overload"))
    headline = "Solid workout execution! Progressive overload is active." if overload_count > 0 else "Focus on progressive tension overload next session."

    recs = []
    if sleep < 7.0:
        recs.append(f"Sleep was {sleep}h. Aim for 7.5–8.5h to optimize human growth hormone (HGH) release and CNS recovery.")
    else:
        recs.append(f"Sleep duration ({sleep}h) is optimal for muscle protein synthesis.")

    if protein < 140:
        recs.append(f"Protein intake ({protein}g) is below optimal hypertrophy threshold. Target at least 1.6–2.0g per kg of bodyweight.")
    else:
        recs.append(f"Protein intake ({protein}g) is dialed in for positive nitrogen balance.")

    recs.append("Add 1 rep or 1.25kg to your primary compound lift in the next workout.")

    return {
        "coach_headline": headline,
        "overload_analysis": f"You have logged {len(workout_history)} sets with {overload_count} progressive overload breakthrough(s).",
        "recovery_analysis": f"Recovery score is {recovery_stats.get('score', 80)}/100 (BMI: {bmi}). Sleep and nutrition are supporting training volume.",
        "recommendations": recs,
        "focus_muscle_group": "Chest & Triceps" if len(workout_history) % 2 == 0 else "Back & Biceps",
        "engine": "Sports Science Heuristic Engine",
    }
