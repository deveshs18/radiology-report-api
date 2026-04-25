# Radiology Report Generator

## Overview
This project generates structured radiology reports by comparing current scan findings with previous scans.

It identifies:
- New findings
- Improved conditions
- Worsening conditions
- Stable findings
- Resolved findings

## Approach

1. Normalized findings into structured format (organ, condition, severity, size)
2. Built comparison logic:
   - Severity-based comparison
   - Size-based comparison
3. Classified findings into:
   - new / improved / worsened / stable
4. Generated:
   - Findings (structured JSON)
   - Impression (clinical summary)
   - Recommendations

## Assumptions
- Severity follows: none < mild < moderate < severe
- Same organ + condition = same finding
- Size is used when severity is equal

## What Worked
- Simple rule-based comparison performed reliably
- Handled edge cases like resolved findings
- Produced consistent structured output

## What Didn’t Work
- No synonym handling (e.g., “mass” vs “lesion”)
- No NLP understanding of free-text reports

## Improvements
- Add NLP for unstructured radiology text
- Use LLM for better impression generation
- Add confidence scores
- Support multi-organ complex cases

## How to Run

```bash
pip install -r requirements.txt
uvicorn main:app --reload