from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Radiology Report Generator")

# -------------------------
# Models
# -------------------------

class Finding(BaseModel):
    organ: str
    condition: str
    severity: str
    size_mm: Optional[float] = None

class Scan(BaseModel):
    findings: List[Finding]

class ReportRequest(BaseModel):
    current_scan: Scan
    previous_scans: List[Scan]

# -------------------------
# Helpers
# -------------------------

SEVERITY_ORDER = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3
}

def finding_key(f: Finding):
    return f"{f.organ.lower()}::{f.condition.lower()}"

def compare_findings(current: Finding, previous: Finding):
    current_sev = SEVERITY_ORDER.get(current.severity.lower(), 0)
    prev_sev = SEVERITY_ORDER.get(previous.severity.lower(), 0)

    # Compare severity
    if current_sev > prev_sev:
        return "worsened"
    elif current_sev < prev_sev:
        return "improved"

    # Compare size if severity same
    if current.size_mm is not None and previous.size_mm is not None:
        if current.size_mm > previous.size_mm:
            return "worsened"
        elif current.size_mm < previous.size_mm:
            return "improved"

    return "stable"

# -------------------------
# Core Logic
# -------------------------

def generate_report(current_scan: Scan, previous_scans: List[Scan]):
    previous_findings_map = {}

    # Flatten previous findings
    for scan in previous_scans:
        for f in scan.findings:
            previous_findings_map[finding_key(f)] = f

    findings_output = []
    impression_output = []
    recommendations = []

    for current_finding in current_scan.findings:
        key = finding_key(current_finding)

        if key not in previous_findings_map:
            status = "new"
            findings_output.append({
                "organ": current_finding.organ,
                "condition": current_finding.condition,
                "status": status,
                "severity": current_finding.severity,
                "size_mm": current_finding.size_mm
            })
            impression_output.append(
                f"New {current_finding.condition} identified in the {current_finding.organ}."
            )
            recommendations.append(
                f"Further evaluation of new {current_finding.condition} in the {current_finding.organ} recommended."
            )

        else:
            previous_finding = previous_findings_map[key]
            status = compare_findings(current_finding, previous_finding)

            findings_output.append({
                "organ": current_finding.organ,
                "condition": current_finding.condition,
                "status": status,
                "severity": current_finding.severity,
                "size_mm": current_finding.size_mm
            })

            if status == "improved":
                impression_output.append(
                    f"{current_finding.condition} in the {current_finding.organ} has improved compared to prior scan."
                )
            elif status == "worsened":
                impression_output.append(
                    f"{current_finding.condition} in the {current_finding.organ} has worsened compared to prior scan."
                )
                recommendations.append(
                    f"Close follow-up for worsening {current_finding.condition} in the {current_finding.organ}."
                )
            else:
                impression_output.append(
                    f"{current_finding.condition} in the {current_finding.organ} is stable."
                )

    # Detect resolved findings
    current_keys = {finding_key(f) for f in current_scan.findings}
    for prev_key, prev_finding in previous_findings_map.items():
        if prev_key not in current_keys:
            impression_output.append(
                f"Previously noted {prev_finding.condition} in the {prev_finding.organ} has resolved."
            )

    return {
        "findings": findings_output,
        "impression": impression_output,
        "recommendations": recommendations
    }

# -------------------------
# API Endpoint
# -------------------------

@app.post("/generate-report")
def generate_radiology_report(request: ReportRequest):
    return generate_report(request.current_scan, request.previous_scans)
