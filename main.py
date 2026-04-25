from fastapi import FastAPI, Request

app = FastAPI()

# -----------------------------
# Helper functions
# -----------------------------

def normalize(text):
    if not text:
        return ""
    return text.lower()


def get_modality(text):
    text = normalize(text)
    if "mri" in text:
        return "mri"
    if "ct" in text:
        return "ct"
    if "x-ray" in text or "xray" in text:
        return "xray"
    return "other"


def get_body_part(text):
    text = normalize(text)

    if "brain" in text or "head" in text:
        return "brain"
    if "chest" in text or "lung" in text:
        return "chest"
    if "abdomen" in text:
        return "abdomen"

    return "other"


def is_relevant(current_desc, prior_desc):
    curr_mod = get_modality(current_desc)
    prior_mod = get_modality(prior_desc)

    curr_body = get_body_part(current_desc)
    prior_body = get_body_part(prior_desc)

    # rule: same body part + same modality = relevant
    if curr_body == prior_body and curr_mod == prior_mod:
        return True

    return False


# -----------------------------
# API endpoint
# -----------------------------

@app.post("/generate-report")
async def generate_report(request: Request):
    try:
        data = await request.json()
        cases = data.get("cases", [])

        predictions = []

        for case in cases:
            case_id = case.get("case_id")
            current = case.get("current_study", {})
            priors = case.get("prior_studies", [])

            current_desc = current.get("study_description", "")

            for prior in priors:
                study_id = prior.get("study_id")
                prior_desc = prior.get("study_description", "")

                predictions.append({
                    "case_id": case_id,
                    "study_id": study_id,
                    "predicted_is_relevant": is_relevant(current_desc, prior_desc)
                })

        return {"predictions": predictions}

    except Exception:
        return {"predictions": []}


# -----------------------------
# Health check
# -----------------------------

@app.get("/")
def health():
    return {"status": "running"}
