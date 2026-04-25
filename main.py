from fastapi import FastAPI, Request
from typing import List, Optional

app = FastAPI()

# -----------------------------
# Helper functions
# -----------------------------

SEVERITY_RANK = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3
}

def normalize_severity(value):
    if not value:
        return "mild"
    value = str(value).lower()
    return value if value in SEVERITY_RANK else "mild"


def get_key(finding):
    organ = finding.get("organ", "").lower()
    condition = finding.get("condition", "").lower()
    return f"{organ}::{condition}"


def compare(current, previous):
    curr_sev = SEVERITY_RANK.get(normalize_severity(current.get("severity")), 1)
    prev_sev = SEVERITY_RANK.get(normalize_severity(previous.get("severity")), 1)

    # severity comparison
    if curr_sev > prev_sev:
        return "worsened"
    if curr_sev < prev_sev:
        return "improved"

    # size comparison (if available)
    curr_size = current.get("size_mm")
    prev_size = previous.get("size_mm")

    if curr_size is not None and prev_size is not None:
        try:
            if float(curr_size) > float(prev_size):
                return "worsened"
            if float(curr_size) < float(prev_size):
                return "improved"
        except:
            pass

    return "stable"


# -----------------------------
# Core logic
# -----------------------------

def process_case(case):
    current = case.get("current_scan", {})
    previous = case.get("previous_scans", [])

    current_findings = current.get("findings", []) if isinstance(current, dict) else []
    previous_findings = []

    # flatten previous scans
    if isinstance(previous, list):
        for scan in previous:
            if isinstance(scan, dict):
                previous_findings.extend(scan.get("findings", []))

    # build lookup map
    prev_map = {}
    for f in previous_findings:
        if isinstance(f, dict):
            prev_map[get_key(f)] = f

    findings_output = []
    impression_output = []
    recommendations = []

    for f in current_findings:
        if not isinstance(f, dict):
            continue

        key = get_key(f)

        if key not in prev_map:
            status = "new"
            impression_output.append(
                f"New {f.get('condition', 'finding')} in {f.get('organ', 'unknown organ')}."
            )
            recommendations.append(
                f"Follow-up suggested for new {f.get('condition', 'finding')}."
            )
        else:
            status = compare(f, prev_map[key])

            if status == "worsened":
                impression_output.append(
                    f"{f.get('condition')} in {f.get('organ')} has worsened."
                )
                recommendations.append(
                    f"Monitor progression of {f.get('condition')}."
                )
            elif status == "improved":
                impression_output.append(
                    f"{f.get('condition')} in {f.get('organ')} has improved."
                )
            else:
                impression_output.append(
                    f"{f.get('condition')} in {f.get('organ')} is stable."
                )

        findings_output.append({
            "organ": f.get("organ", "unknown"),
            "condition": f.get("condition", "unknown"),
            "status": status,
            "severity": normalize_severity(f.get("severity")),
            "size_mm": f.get("size_mm")
        })

    return {
        "findings": findings_output,
        "impression": impression_output,
        "recommendations": recommendations
    }


# -----------------------------
# API endpoint
# -----------------------------

@app.post("/generate-report")
async def generate_report(request: Request):
    try:
        data = await request.json()

        # support both single and batch input
        if isinstance(data, dict):
            data = [data]

        predictions = []

        for case in data:
            if not isinstance(case, dict):
                predictions.append({
                    "findings": [],
                    "impression": ["Invalid input format"],
                    "recommendations": []
                })
                continue

            result = process_case(case)
            predictions.append(result)

        return {"predictions": predictions}

    except Exception as e:
        return {
            "predictions": [
                {
                    "findings": [],
                    "impression": ["Error processing request"],
                    "recommendations": [],
                    "error": str(e)
                }
            ]
        }


# -----------------------------
# Health check
# -----------------------------

@app.get("/")
def health():
    return {"status": "running"}
