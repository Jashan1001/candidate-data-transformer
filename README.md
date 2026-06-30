# Multi-Source Candidate Data Transformer

> Eightfold AI Engineering Intern Assignment (Jul–Dec 2026)

A production-inspired ETL pipeline that consolidates candidate information from multiple heterogeneous sources into a single canonical profile with deterministic conflict resolution, provenance tracking, confidence scoring, and configurable output projection.

---

## Repository Highlights

✅ Structured + Unstructured sources

✅ Canonical candidate profile

✅ Field-level provenance

✅ Confidence scoring

✅ Configurable output projection

✅ Two-stage validation

✅ Graceful degradation

✅ 100+ automated tests

---

## Demo

### CLI Execution

> *(Insert screenshot here)*

![CLI](assets/cli_demo.png)

---

### Default Output

> *(Insert screenshot here)*

![Default Output](assets/output_default.png)

---

### Custom Output

> *(Insert screenshot here)*

![Custom Output](assets/output_custom.png)

---

## Architecture

> *(Insert architecture diagram here)*

![Architecture](assets/architecture.png)

```text
Recruiter CSV
ATS JSON
GitHub
Resume
      │
      ▼
Extractors
      ▼
RawCandidate
      ▼
Merge Engine
      ▼
CanonicalProfile
      ▼
Confidence
      ▼
Validation
      ▼
Projection
      ▼
Output Validation
      ▼
Final JSON
```

---

# Features

- Supports structured and unstructured candidate sources.
- Normalizes names, emails, phones, locations, skills, and dates.
- Merges conflicting observations using deterministic field-specific strategies.
- Preserves field-level provenance for every resolved value.
- Computes overall profile confidence.
- Projects the canonical profile into configurable JSON using `OutputConfig`.
- Validates both the canonical profile and projected output.
- Continues processing when recoverable source failures occur.

---

# Supported Sources

| Source | Type |
|---------|------|
| Recruiter CSV | Structured |
| ATS JSON (Greenhouse / Lever / Generic) | Structured |
| GitHub Profile | Unstructured |
| Resume (PDF / DOCX) | Unstructured |

---

# Quick Start

Clone the repository.

```bash
git clone https://github.com/Jashan1001/candidate-data-transformer.git

cd candidate-data-transformer
```

Create a virtual environment.

```bash
python -m venv .venv

source .venv/bin/activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Run the pipeline.

```bash
python -m transformer.cli \
    --csv input/recruiter.csv \
    --ats input/ats/sample.json \
    --resume input/resumes/aarav_mehta_resume.pdf \
    --github aaravmehta \
    --config input/configs/default.json \
    --output output/default.json
```

---

# Sample Output

```json
{
  "candidate_id": "...",
  "full_name": "Aarav Mehta",
  "emails": [
    "aarav.mehta@example.com"
  ],
  "phones": [
    "+919876543210"
  ],
  "skills": [
    {
      "name": "python",
      "confidence": 0.97
    }
  ],
  "overall_confidence": 0.94
}
```

*(Use your actual generated output.)*

---

# Runtime Configuration

The output schema is controlled through a runtime `OutputConfig`.

Supported capabilities include:

- Field selection
- Field renaming
- Nested output paths
- Runtime normalization
- Required field validation
- Missing field handling (`null`, `omit`, `error`)
- Optional confidence output
- Optional provenance output

The internal `CanonicalProfile` remains unchanged while different consumers receive different output schemas.

---

# Edge Cases Handled

- Duplicate emails, phones, and skills across multiple sources are normalized and deduplicated.
- Conflicting scalar values are resolved using deterministic source priority.
- Malformed ATS JSON or missing input files do not terminate the pipeline.
- GitHub API failures degrade gracefully without blocking the remaining sources.
- Missing required projection fields raise clear validation errors.

---

# Testing

Run the complete test suite.

```bash
pytest
```

Lint the project.

```bash
ruff check .
```

Format the project.

```bash
ruff format .
```

---

# Repository Structure

```text
src/
    extractors/
    merger/
    models/
    normalizers/
    confidence/
    projector/
    validator/

tests/

input/

output/

docs/
```

---

# Design Document

The architecture decisions, merge strategy, normalization policy, confidence model, edge cases, and trade-offs are documented in:

```
docs/design.md
```

The original one-page design submission is also included:

```
docs/JashanpreetKaur_jashan100106@gmail.com_Eightfold.pdf
```

---

# Known Limitations

- LinkedIn integration is intentionally excluded due to the lack of a public, terms-compliant API.
- Automatic cross-candidate identity resolution is out of scope.
- OCR for scanned resumes is not currently supported.

---

# Future Work

- Additional ATS integrations
- Recruiter notes parser
- Parallel extraction
- Streaming ingestion
- LLM-assisted resume parsing

---

# Demo Video

🎥 *(Add YouTube / Drive link after recording.)*

---

# License

MIT License