from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, computed_field
from typing import Literal, Annotated, Optional
import pickle, pandas as pd

with open("model.pkl", "rb") as f:
    model = pickle.load(f)

app = FastAPI(title="InsureIQ API", version="3.0.0", redirect_slashes=False)

TIER_1 = {"Mumbai","Delhi","Bangalore","Chennai","Kolkata","Hyderabad","Pune"}
TIER_2 = {
    "Jaipur","Chandigarh","Indore","Lucknow","Patna","Ranchi","Visakhapatnam",
    "Coimbatore","Bhopal","Nagpur","Vadodara","Surat","Rajkot","Jodhpur",
    "Raipur","Amritsar","Varanasi","Agra","Dehradun","Mysore","Jabalpur",
    "Guwahati","Thiruvananthapuram","Ludhiana","Nashik","Allahabad","Udaipur",
    "Aurangabad","Hubli","Belgaum","Salem","Vijayawada","Tiruchirappalli",
    "Bhavnagar","Gwalior","Dhanbad","Bareilly","Aligarh","Gaya","Kozhikode",
    "Warangal","Kolhapur","Bilaspur","Jalandhar","Noida","Guntur","Asansol","Siliguri",
}

POLICIES = {
    "Low":    [{"name":"BasicCare Plan","coverage":"3 Lakh","premium_range":"4,000-6,000/yr","highlights":["Hospitalisation cover","Daycare procedures","Free annual check-up"]}],
    "Medium": [{"name":"GoldShield Plan","coverage":"10 Lakh","premium_range":"10,000-16,000/yr","highlights":["Critical illness rider","OPD cover 5,000","No-claim bonus"]}],
    "High":   [{"name":"ComprehensivePlus Plan","coverage":"25 Lakh","premium_range":"22,000-35,000/yr","highlights":["International emergency cover","Mental health cover","Room rent waiver","Personal accident rider"]}],
}

HEALTH_TIPS = {
    "Low":    {"headline":"Great job - keep it up!","tips":["Maintain 150 min of moderate exercise/week","Balanced diet rich in vegetables","Annual health check-up","7-8 hours of quality sleep"]},
    "Medium": {"headline":"Room to improve - small changes, big results","tips":["Aim for BMI below 27","Consider smoking cessation programme","30 min brisk walk 5 days/week","Reduce processed food","Monitor BP & cholesterol every 6 months"]},
    "High":   {"headline":"Action needed - your health is your wealth","tips":["Consult doctor for weight-management plan","Quit smoking immediately","Low-GI diet, reduce salt & saturated fats","Start 20 min low-impact exercise daily","Get comprehensive blood work done","Stress management: yoga, meditation"]},
}

BASE_PREMIUMS = {"High": 28000, "Medium": 13000, "Low": 5500}

OccupationType = Literal["retired","freelancer","student","government_job","business_owner","unemployed","private_job"]

class UserInput(BaseModel):
    age:        Annotated[int,   Field(..., gt=0, lt=120)]
    weight:     Annotated[float, Field(..., gt=0)]
    height:     Annotated[float, Field(..., gt=0, lt=2.5)]
    income_lpa: Annotated[float, Field(..., gt=0)]
    smoker:     bool
    city:       str
    occupation: OccupationType

    @computed_field
    @property
    def bmi(self) -> float:
        return round(self.weight / (self.height ** 2), 2)

    @computed_field
    @property
    def lifestyle_risk(self) -> str:
        if self.smoker and self.bmi > 30: return "high"
        elif self.smoker or self.bmi > 27: return "medium"
        return "low"

    @computed_field
    @property
    def age_group(self) -> str:
        if self.age < 25: return "young"
        elif self.age < 45: return "adult"
        elif self.age < 60: return "middle_aged"
        return "senior"

    @computed_field
    @property
    def city_tier(self) -> int:
        if self.city in TIER_1: return 1
        elif self.city in TIER_2: return 2
        return 3


class OptimizeRequest(BaseModel):
    age:             int
    weight:          float
    height:          float
    income_lpa:      float
    smoker:          bool
    city:            str
    occupation:      OccupationType
    target_category: Literal["Low", "Medium"] = "Low"


def _predict_from_input(data: UserInput) -> str:
    df = pd.DataFrame([{
        "bmi": data.bmi, "age_group": data.age_group,
        "lifestyle_risk": data.lifestyle_risk, "city_tier": data.city_tier,
        "income_lpa": data.income_lpa, "occupation": data.occupation,
    }])
    return model.predict(df)[0]


def _shap_text(features: dict) -> list[str]:
    try:
        from explainer import get_text_explanation
        return get_text_explanation(features, features.get("predicted_category", "Medium"))
    except Exception:
        lines = []
        if features.get("smoker"):
            lines.append("Smoker status significantly increased your risk")
        if features.get("bmi", 0) > 30:
            lines.append(f"BMI of {features['bmi']:.1f} (obese range) raised your risk")
        elif features.get("bmi", 0) > 27:
            lines.append(f"BMI of {features['bmi']:.1f} (overweight) moderately raised risk")
        if features.get("age_group") == "senior":
            lines.append("Senior age group contributes to higher risk")
        elif features.get("age_group") == "young":
            lines.append("Young age group reduced your risk")
        if features.get("lifestyle_risk") == "high":
            lines.append("Combined lifestyle factors (BMI + smoking) flagged as high risk")
        return lines or ["Risk driven by combination of health and lifestyle factors"]


@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0.0"}


@app.post("/predict")
def predict(data: UserInput):
    prediction = _predict_from_input(data)
    feat = {
        "bmi": data.bmi, "age_group": data.age_group,
        "lifestyle_risk": data.lifestyle_risk, "city_tier": data.city_tier,
        "income_lpa": data.income_lpa, "occupation": data.occupation,
        "smoker": data.smoker, "predicted_category": prediction,
    }
    shap_chart = None
    try:
        from explainer import get_shap_chart_b64
        shap_chart = get_shap_chart_b64(feat)
    except Exception:
        pass

    return JSONResponse(status_code=200, content={
        "predicted_category": prediction,
        "derived_features":   {"bmi": data.bmi, "age_group": data.age_group,
                               "lifestyle_risk": data.lifestyle_risk, "city_tier": data.city_tier},
        "health_tips":        HEALTH_TIPS.get(prediction, {}),
        "policies":           POLICIES.get(prediction, []),
        "shap_explanation":   _shap_text(feat),
        "shap_chart_b64":     shap_chart,
    })


@app.post("/optimize")
def optimize(req: OptimizeRequest):
    base    = UserInput(**req.model_dump(exclude={"target_category"}))
    current = _predict_from_input(base)

    if current == req.target_category:
        return JSONResponse(content={
            "message": "You are already at target!", "scenarios": [], "current_category": current
        })

    scenarios = []

    if req.smoker:
        test = UserInput(**{**req.model_dump(exclude={"target_category"}), "smoker": False})
        cat  = _predict_from_input(test)
        save = max(0, BASE_PREMIUMS.get(current, 13000) - BASE_PREMIUMS.get(cat, 13000))
        scenarios.append({
            "action": "Quit smoking", "result_category": cat,
            "reaches_target": cat == req.target_category,
            "estimated_annual_savings": save,
            "difficulty": "Hard", "timeline": "3-6 months with support",
            "change_detail": "Smoker: Yes -> No",
        })

    for kg in [2, 4, 6, 8, 10, 15, 20]:
        new_w = max(40.0, req.weight - kg)
        test  = UserInput(**{**req.model_dump(exclude={"target_category"}), "weight": new_w})
        cat   = _predict_from_input(test)
        save  = max(0, BASE_PREMIUMS.get(current, 13000) - BASE_PREMIUMS.get(cat, 13000))
        new_bmi = round(new_w / (req.height ** 2), 1)
        scenarios.append({
            "action": f"Lose {kg} kg", "result_category": cat,
            "reaches_target": cat == req.target_category,
            "estimated_annual_savings": save,
            "difficulty": "Easy" if kg <= 4 else "Medium" if kg <= 10 else "Hard",
            "timeline": f"~{kg * 2} weeks with 500 kcal/day deficit",
            "change_detail": f"Weight: {req.weight} kg -> {new_w} kg | BMI: {round(req.weight/req.height**2,1)} -> {new_bmi}",
        })
        if cat == req.target_category:
            break

    if req.smoker:
        for kg in [2, 4, 6, 10]:
            new_w = max(40.0, req.weight - kg)
            test  = UserInput(**{**req.model_dump(exclude={"target_category"}), "weight": new_w, "smoker": False})
            cat   = _predict_from_input(test)
            save  = max(0, BASE_PREMIUMS.get(current, 13000) - BASE_PREMIUMS.get(cat, 13000))
            scenarios.append({
                "action": f"Quit smoking + Lose {kg} kg", "result_category": cat,
                "reaches_target": cat == req.target_category,
                "estimated_annual_savings": save,
                "difficulty": "Hard", "timeline": "3-6 months",
                "change_detail": f"Smoker: No, Weight: {req.weight} -> {new_w} kg",
            })
            if cat == req.target_category:
                break

    scenarios.sort(key=lambda x: (not x["reaches_target"], -x["estimated_annual_savings"]))

    return JSONResponse(content={
        "current_category": current,
        "target_category":  req.target_category,
        "scenarios":        scenarios[:6],
    })


@app.post("/parse-report")
async def parse_report(file: UploadFile = File(...)):
    ext = "." + file.filename.split(".")[-1].lower()
    if ext not in {".pdf", ".jpg", ".jpeg", ".png"}:
        raise HTTPException(400, "Only PDF, JPG, PNG files are supported.")
    try:
        from report_parser import parse_report as _parse
        content = await file.read()
        return JSONResponse(content=_parse(content, file.filename))
    except ImportError:
        raise HTTPException(500, "Install: pip install anthropic PyMuPDF pillow")
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/wearable/{user_id}")
def get_wearable(user_id: int):
    try:
        from wearable import get_wearable_summary
        return JSONResponse(content=get_wearable_summary(user_id))
    except ImportError:
        raise HTTPException(500, "wearable module not found.")


@app.post("/wearable/apply-discount")
def apply_discount(payload: dict):
    try:
        from wearable import apply_wearable_discount
        return JSONResponse(content=apply_wearable_discount(
            payload.get("predicted_category", "Medium"),
            payload.get("discount_pct", 0.0),
        ))
    except ImportError:
        raise HTTPException(500, "wearable module not found.")


@app.get("/benchmark/{user_id}")
def benchmark(user_id: int, city: str = "", age: int = 25):
    try:
        import database as db
        all_preds  = db.get_all_predictions_flat()
        user_preds = db.get_user_predictions(user_id, limit=1)

        if not user_preds:
            return JSONResponse(content={"message": "Make a prediction first!", "percentile": None})

        cat_score  = {"Low": 100, "Medium": 50, "High": 0}
        user_cat   = user_preds[0]["predicted_category"]
        user_score = cat_score.get(user_cat, 50)

        city_preds = [p for p in all_preds if p.get("city","").lower() == city.lower()] if city else all_preds
        age_preds  = [p for p in all_preds if abs((p.get("age") or 0) - age) <= 5]

        def percentile(preds):
            if not preds: return None
            scores = [cat_score.get(p["predicted_category"], 50) for p in preds]
            return int(sum(1 for s in scores if s <= user_score) / len(scores) * 100)

        total = len(all_preds)
        dist  = {cat: {"count": sum(1 for p in all_preds if p["predicted_category"] == cat),
                        "pct": round(sum(1 for p in all_preds if p["predicted_category"] == cat) / total * 100) if total else 0}
                 for cat in ["Low", "Medium", "High"]}

        age_cohort = f"users aged {max(18,age-5)}-{age+5}"
        trend = None
        if age_preds:
            lp = sum(1 for p in age_preds if p["predicted_category"] == "Low") / len(age_preds) * 100
            trend = f"{lp:.0f}% of {age_cohort} are in the Low risk category"

        return JSONResponse(content={
            "user_category":   user_cat,
            "city_percentile": percentile(city_preds),
            "age_percentile":  percentile(age_preds),
            "total_users":     total,
            "city_sample":     len(city_preds),
            "age_sample":      len(age_preds),
            "category_dist":   dist,
            "trend_message":   trend,
            "city":            city,
            "age_cohort":      age_cohort,
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "percentile": None})