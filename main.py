from fastapi import FastAPI, Request
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI(title="Radiology Report Generator")

class Finding(BaseModel):
    organ: str
    condition: str
    severity: str
    size_mm: Optional[float] = None

class Scan(BaseModel):
    findings: List[Finding]

SEVERITY_ORDER = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3
}

def normalize_severity(sev):
    if not sev:
        return "mild"
    sev = str(sev).lower()
    return sev if sev in SEVERITY_ORDER else "mild"

def finding_key(f: Finding):
    return f"{f.organ.lower()}::{f.condition.lower()}"

def compare_findings(current: Finding, previous: Finding):
    current_sev = SEVERITY_ORDER.get(normalize_severity(current.severity), 1)
    prev_sev = SEVERITY_ORDER.get(normalize_severity(previous.severity), 1)

    if current_sev > prev_sev:
        return "worsened"
    elif current_sev < prev_sev:
        return "improved"

    if current.size_mm is not None and previous.size_mm is not None:
        if current.size_mm > previous.size_mm:
            return "worsened"
        elif current.size_mm < previous.size_mm:
            return "improved"

    return "stable"

def generate_report(current_scan: Scan, previous_scans: List[Scan]):
    previous_map = {}

    for scan in previous_scans:
        for f in scan.findings:
            previous_map[finding_key(f)] = f

    findings_output = []
    impression_output = []
    recommendations = []

    for curr in current_scan.findings:
        key = finding_key(curr)

        if key not in previous_map:
            status = "new"
            findings_output.append({
                "organ": curr.organ,
                "condition": curr.condition,
                "status": status,
                "severity": curr.severity,
                "size_mm": curr.size_mm
            })
            impression_output.append(
                f"New {curr.condition} identified in the {curr.organ}."
            )
            recommendations.append(
                f"Further evaluation recommended for new {curr.condition} in the {curr.organ}."
            )
        else:
            prev = previous_map[key]
            status = compare_findings(curr, prev)

            findings_output.append({
                "organ": curr.organ,
                "condition": curr.condition,
                "status": status,
                "severity": curr.severity,
                "size_mm": curr.size_mm
            })

            if status == "improved":
                impression_output.append(
                    f"{curr.condition} in the {curr.organ} has improved compared to prior scan."
                )
            elif status == "worsened":
                impression_output.append(
                    f"{curr.condition} in the {curr.organ} has worsened compared to prior scan."
                )
                recommendations.append(
                    f"Close monitoring recommended for worsening {curr.condition}."
                )
            else:
                impression_output.append(
                    f"{curr.condition} in the {curr.organ} is stable."
                )

    current_keys = {finding_key(f) for f in current_scan.findings}
    for key, prev in previous_map.items():
        if key not in current_keys:
            impression_output.append(
                f"Previously noted {prev.condition} in the {prev.organ} has resolved."
            )

    return {
        "findings": findings_output,
        "impression": impression_output,
        "recommendations": recommendations
    }

@app.post("/generate-report")
async def generate_radiology_report(request: Request):
    try:
        data = await request.json()

        # flexible input handling
        current_data = data.get("current_scan", {})
        previous_data = data.get("previous_scans", [])

        if not isinstance(previous_data, list):
            previous_data = []

        current_findings_raw = current_data.get("findings", [])

        previous_findings_raw = []
        for scan in previous_data:
            if isinstance(scan, dict):
                previous_findings_raw.extend(scan.get("findings", []))

        def safe_finding(f):
            return Finding(
                organ=str(f.get("organ", "unknown")),
                condition=str(f.get("condition", "unknown")),
                severity=normalize_severity(f.get("severity")),
                size_mm=f.get("size_mm")
            )

        current_findings = [safe_finding(f) for f in current_findings_raw if isinstance(f, dict)]
        previous_findings = [safe_finding(f) for f in previous_findings_raw if isinstance(f, dict)]

        current_scan = Scan(findings=current_findings)
        previous_scans = [Scan(findings=previous_findings)]

        result = generate_report(current_scan, previous_scans)

        return {
            "predictions": [result]
        }

    except Exception as e:
        return {
            "predictions": [
                {
                    "findings": [],
                    "impression": ["Unable to process input"],
                    "recommendations": [],
                    "error": str(e)
                }
            ]
        }

@app.get("/")
def health_check():
    return {"status": "API is running"}
