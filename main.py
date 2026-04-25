from fastapi import FastAPI, Request

app = FastAPI()

SEVERITY_RANK = {
    "none": 0,
    "mild": 1,
    "moderate": 2,
    "severe": 3
}


def normalize(sev):
    if not sev:
        return "mild"
    sev = str(sev).lower()
    return sev if sev in SEVERITY_RANK else "mild"


def compare(curr, prev):
    c = SEVERITY_RANK.get(normalize(curr.get("severity")), 1)
    p = SEVERITY_RANK.get(normalize(prev.get("severity")), 1)

    if c > p:
        return "worsened"
    if c < p:
        return "improved"

    # fallback
    return "stable"


def get_label(current_findings, previous_findings):
    # simple heuristic: compare first matching finding
    for curr in current_findings:
        for prev in previous_findings:
            if curr.get("organ") == prev.get("organ") and curr.get("condition") == prev.get("condition"):
                return compare(curr, prev)

    # if nothing matches
    if current_findings and not previous_findings:
        return "new"

    return "stable"


@app.post("/generate-report")
async def generate_report(request: Request):
    try:
        data = await request.json()

        # handle all formats
        if isinstance(data, dict):
            if "cases" in data:
                cases = data["cases"]
            else:
                cases = [data]
        else:
            cases = data

        predictions = []

        for case in cases:
            current = case.get("current_scan", {})
            previous_scans = case.get("previous_scans", [])

            current_findings = current.get("findings", []) if isinstance(current, dict) else []

            # 🔥 IMPORTANT: generate prediction PER previous scan
            for prev in previous_scans:
                prev_findings = prev.get("findings", []) if isinstance(prev, dict) else []

                label = get_label(current_findings, prev_findings)

                predictions.append({
                    "label": label
                })

        return {"predictions": predictions}

    except Exception as e:
        return {
            "predictions": [
                {"label": "stable"}
            ]
        }
