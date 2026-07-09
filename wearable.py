"""
wearable.py  —  Feature 3: Digital Twin Wearable Sync
Mock Google Fit / Apple Health data with realistic simulation.
In production: replace _mock_fetch with real OAuth2 + Google Fit REST API calls.
"""

import random
from datetime import datetime, timedelta


# ── Mock data generator ────────────────────────────────────────────────────────

def _mock_fetch_fit_data(user_id: int, days: int = 30) -> list[dict]:
    """
    Simulates 30 days of wearable data per user.
    Seed is user_id so the same user always gets consistent data.
    """
    rng = random.Random(user_id * 42)
    records = []
    base_steps       = rng.randint(5000, 12000)
    base_sleep       = round(rng.uniform(5.5, 8.0), 1)
    base_heart_rate  = rng.randint(58, 90)

    for i in range(days):
        date = (datetime.today() - timedelta(days=i)).strftime("%Y-%m-%d")
        records.append({
            "date":            date,
            "steps":           max(0, base_steps + rng.randint(-2000, 2000)),
            "sleep_hours":     round(max(3, base_sleep + rng.uniform(-1.5, 1.5)), 1),
            "resting_hr":      max(45, base_heart_rate + rng.randint(-8, 8)),
            "active_minutes":  max(0, rng.randint(10, 90)),
            "calories_burned": max(1200, rng.randint(1600, 3000)),
        })
    return records


# ── Analytics ─────────────────────────────────────────────────────────────────

def get_wearable_summary(user_id: int) -> dict:
    """
    Returns a 30-day summary of the user's wearable data
    + a lifestyle_discount to apply to the prediction.
    """
    records = _mock_fetch_fit_data(user_id)

    avg_steps      = int(sum(r["steps"]       for r in records) / len(records))
    avg_sleep      = round(sum(r["sleep_hours"] for r in records) / len(records), 1)
    avg_hr         = int(sum(r["resting_hr"]  for r in records) / len(records))
    avg_active_min = int(sum(r["active_minutes"] for r in records) / len(records))

    # ── Lifestyle score (0–100) ───────────────────────────────────────────────
    score = 0

    # Steps scoring (WHO: 8,000+ is good, 10,000+ is great)
    if avg_steps >= 10000:
        score += 40
    elif avg_steps >= 8000:
        score += 30
    elif avg_steps >= 6000:
        score += 18
    else:
        score += 5

    # Sleep scoring (7–9 hrs is optimal)
    if 7 <= avg_sleep <= 9:
        score += 30
    elif 6 <= avg_sleep < 7 or 9 < avg_sleep <= 10:
        score += 18
    else:
        score += 5

    # Heart rate scoring (lower resting HR = better fitness)
    if avg_hr < 60:
        score += 20
    elif avg_hr < 70:
        score += 14
    elif avg_hr < 80:
        score += 8
    else:
        score += 2

    # Active minutes (WHO: 150+ min/week = 21+ min/day)
    if avg_active_min >= 30:
        score += 10
    elif avg_active_min >= 21:
        score += 6
    else:
        score += 2

    # ── Discount calculation ──────────────────────────────────────────────────
    # Max 15% discount for perfect lifestyle score
    discount_pct = round((score / 100) * 15, 1)

    # ── Badge / tier ─────────────────────────────────────────────────────────
    if score >= 80:
        badge = "Elite Athlete"
        badge_color = "#22c55e"
    elif score >= 60:
        badge = "Active Lifestyle"
        badge_color = "#3b82f6"
    elif score >= 40:
        badge = "Moderate Activity"
        badge_color = "#f59e0b"
    else:
        badge = "Sedentary"
        badge_color = "#ef4444"

    # ── Insights ─────────────────────────────────────────────────────────────
    insights = []
    if avg_steps >= 10000:
        insights.append(f"Great job! Averaging {avg_steps:,} steps/day earns you a full activity bonus.")
    elif avg_steps < 6000:
        insights.append(f"Your {avg_steps:,} steps/day is below the 8,000 target — try a 20-min walk daily.")

    if avg_sleep < 6.5:
        insights.append(f"Only {avg_sleep} hrs sleep/night detected — poor sleep increases insurance risk.")
    elif avg_sleep >= 7:
        insights.append(f"Solid {avg_sleep} hrs of sleep/night — keeps cortisol and inflammation low.")

    if avg_hr > 80:
        insights.append(f"Resting HR of {avg_hr} bpm is elevated — regular cardio can bring it under 70.")
    elif avg_hr < 65:
        insights.append(f"Resting HR of {avg_hr} bpm shows excellent cardiovascular fitness.")

    return {
        "avg_steps":       avg_steps,
        "avg_sleep_hours": avg_sleep,
        "avg_resting_hr":  avg_hr,
        "avg_active_min":  avg_active_min,
        "lifestyle_score": score,
        "lifestyle_badge": badge,
        "badge_color":     badge_color,
        "discount_pct":    discount_pct,
        "insights":        insights,
        "days_synced":     len(records),
        "last_sync":       records[0]["date"],
        "daily_records":   records[:7],  # last 7 days for chart
    }


def apply_wearable_discount(predicted_category: str, discount_pct: float) -> dict:
    """
    Applies lifestyle discount to a predicted category.
    Returns adjusted category + savings estimate.
    """
    # Premium estimates per category (annual, mid-range plan)
    base_premiums = {"High": 28000, "Medium": 13000, "Low": 5500}
    base = base_premiums.get(predicted_category, 13000)
    savings = round(base * discount_pct / 100)

    # Category upgrade logic (High→Medium if discount ≥ 10%)
    upgraded_category = predicted_category
    if predicted_category == "High" and discount_pct >= 10:
        upgraded_category = "Medium"
    elif predicted_category == "Medium" and discount_pct >= 12:
        upgraded_category = "Low"

    return {
        "original_category":  predicted_category,
        "adjusted_category":  upgraded_category,
        "discount_pct":       discount_pct,
        "estimated_savings":  savings,
        "category_upgraded":  upgraded_category != predicted_category,
    }
