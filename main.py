from fastapi import FastAPI, Request

app = FastAPI()

# -----------------------------
# Normalization helpers
# -----------------------------

def normalize(text):
    return str(text).lower() if text else ""


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

    if any(x in text for x in ["brain", "head", "cranial"]):
        return "brain"
    if any(x in text for x in ["chest", "lung"]):
        return "chest"
    if "abdomen" in text:
        return "abdomen"

    return "other"


def keyword_overlap(a, b):
    words_a = set(normalize(a).split())
    words_b = set(normalize(b).split())
    return len(words_a & words_b)


def is_relevant(curr_desc, prior_desc):
    curr_body = get_body_part(curr_desc)
    prior_body = get_body_part(prior_desc)

    curr_mod = get_modality(curr_desc)
    prior_mod = get_modality(prior_desc)

    if curr_body == prior_body:
        return True

    if keyword_overlap(curr_desc, prior_desc) >= 2:
        return True

    if curr_mod == prior_mod and curr_body != "other" and prior_body != "other":
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

            curr_desc = current.get("study_description", "")

            for prior in priors:
                predictions.append({
                    "case_id": case_id,
                    "study_id": prior.get("study_id"),
                    "predicted_is_relevant": is_relevant(
                        curr_desc,
                        prior.get("study_description", "")
                    )
                })

        return {"predictions": predictions}

    except Exception:
        return {"predictions": []}


@app.get("/")
def health():
    return {"status": "running"}
