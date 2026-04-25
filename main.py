from fastapi import FastAPI, Request
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI(title="Radiology Report Generator")

# -------------------------
# Models (kept for internal use)
# -------------------------

class Finding(BaseModel):
    organ: str
    condition: str
    severity: str
    size_mm: Optional[float] = None

class Scan(BaseModel):
    findings: List[Finding]

# -------------------------
# Helpers
# -------------------------

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
                f"Further evaluation recommended for new {current_finding.condition} in the {current_finding.organ}."
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
                    f"Close monitoring recommended for worsening {current_finding.condition}."
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
# Flexible API Endpoint (FIXES 422)
# -------------------------

@app.post("/generate-report")
async def generate_radiology_report(request: Request):
    try:
        data = await request.json()

        # Handle flexible input
        current_scan_data = data.get("current_scan", {})
        previous_scans_data = data.get("previous_scans", [])

        if not isinstance(previous_scans_data, list):
            previous_scans_data = []

        # Extract current findings
        current_findings_raw = current_scan_data.get("findings", [])

        # Extract previous findings
        previous_findings_raw = []
        for scan in previous_scans_data:
            if isinstance(scan, dict):
                previous_findings_raw.extend(scan.get("findings", []))

        # Safe conversion
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

        return generate_report(current_scan, previous_scans)

    except Exception as e:
        return {
            "findings": [],
            "impression": ["Unable to process input"],
            "recommendations": [],
            "error": str(e)
        }

# -------------------------
# Health check (optional but helpful)
# -------------------------

@app.get("/")
def health_check():
    return {"status": "API is running"}
