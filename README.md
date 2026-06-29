# 🚀 Candidate Data Transformer

> A production-inspired ETL pipeline that consolidates candidate information from multiple heterogeneous sources into a single canonical profile with intelligent merging, confidence scoring, and complete field-level provenance tracking.

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063)
![Pytest](https://img.shields.io/badge/Tested%20With-Pytest-0A9EDC)
![Ruff](https://img.shields.io/badge/Linter-Ruff-D7FF64)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📖 Overview

Recruiters and hiring platforms often receive candidate information from multiple independent sources such as recruiter spreadsheets, Applicant Tracking Systems (ATS), GitHub profiles, and resumes.

These sources frequently contain **duplicate**, **incomplete**, or **conflicting** information. Simply combining the data is not sufficient—values must be normalized, conflicts resolved, confidence estimated, and every decision should remain explainable.

**Candidate Data Transformer** is a modular, production-inspired ETL pipeline that solves this problem by:

- Extracting candidate data from heterogeneous sources
- Normalizing inconsistent formats
- Merging records into a canonical candidate profile
- Tracking provenance for every merged field
- Computing confidence scores based on source reliability and agreement
- Producing configurable JSON output through a projection layer

The project emphasizes **clean architecture**, **extensibility**, and **maintainability**, making it easy to add new data sources or output formats without changing the core pipeline.

---

# ✨ Features

## Multi-Source Candidate Ingestion

The transformer consolidates candidate information from multiple independent sources into a unified profile.

Supported sources include:

- 📄 Recruiter CSV
- 🗂 ATS JSON
- 💻 GitHub Profile
- 📑 Resume (PDF / DOCX)

The architecture is intentionally extensible, allowing additional extractors (e.g., LinkedIn exports or recruiter notes) to be added with minimal changes.

---

## Intelligent Data Normalization

Raw candidate data is normalized before merging to ensure consistency across sources.

Current normalization includes:

- Phone numbers → E.164 format
- Email addresses → lowercase & validated
- Skills → canonical skill names
- Dates → standardized format
- Locations → structured representation
- Candidate names → cleaned and normalized

---

## Intelligent Merge Engine

Instead of blindly overwriting values, the merge engine applies field-specific merge strategies.

### Scalar Fields

Fields such as:

- Full Name
- Headline
- Years of Experience

are resolved using:

1. Source priority
2. Confidence score
3. Conflict penalty

---

### List Fields

Fields such as:

- Emails
- Phone Numbers
- Portfolio URLs

are merged using:

- Union
- Deduplication
- Source-priority ordering

---

### Complex Fields

Structured entities including:

- Skills
- Experience
- Education

are merged using dedicated merge strategies while preserving confidence and provenance.

---

## Confidence Scoring

Every merged profile receives an overall confidence score between **0.0** and **1.0**.

Confidence is computed using multiple independent signals:

- Source reliability
- Extraction confidence
- Multi-source agreement
- Candidate profile completeness

---

## Complete Field-Level Provenance

Every resolved field records:

- Winning source
- Extraction method
- Confidence
- Original value
- All contributing sources

This makes every merge decision transparent and explainable.

---

## Configuration-Driven Projection

The output format is entirely controlled through runtime configuration.

Features include:

- Field selection
- Field renaming
- Nested output paths
- Runtime normalization
- Required field validation
- Optional provenance
- Optional confidence

No code changes are required to generate different output schemas.

---

## Production-Oriented Architecture

The project follows a modular architecture with clear separation of responsibilities.

Core modules include:

- Extractors
- Merge Engine
- Confidence Engine
- Validator
- Projector
- CLI Interface

Each component has a single responsibility and can evolve independently.

---

## Automated Testing

The project includes comprehensive automated tests covering:

- Extractors
- Merge Engine
- Projector
- Validator
- Confidence Engine
- Normalizers
- End-to-end pipeline behaviour

---

# 🏗️ System Architecture

The Candidate Data Transformer follows a modular ETL (Extract → Transform → Load) architecture.

Each stage has a single responsibility and communicates through well-defined data models, making the pipeline easy to extend, test, and maintain.

```text
                    Candidate Data Sources

        Recruiter CSV     ATS JSON      GitHub      Resume
              │              │             │            │
              └──────────────┼─────────────┼────────────┘
                             │
                             ▼
                   +----------------------+
                   |      Extractors      |
                   +----------------------+
                             │
                             ▼
                     RawCandidate Models
                             │
                             ▼
                   +----------------------+
                   |     Merge Engine     |
                   +----------------------+
                             │
             ┌───────────────┼────────────────┐
             │               │                │
             ▼               ▼                ▼
      Normalization   Conflict Resolution   Provenance
             │               │                │
             └───────────────┼────────────────┘
                             ▼
                    CanonicalProfile
                             │
              ┌──────────────┼───────────────┐
              ▼              ▼               ▼
      Confidence Engine   Validator     Projector
              │                              │
              └──────────────┬───────────────┘
                             ▼
                     Configurable JSON Output
```

---

# Pipeline Overview

The transformation pipeline consists of six independent stages:

```text
Extract
   │
   ▼
Merge
   │
   ▼
Confidence Scoring
   │
   ▼
Profile Validation
   │
   ▼
Projection
   │
   ▼
Output Validation
   │
   ▼
Final JSON
```

Each stage operates independently and communicates through strongly-typed domain models, allowing components to evolve without affecting the rest of the pipeline.

---

# Internal Data Flow

The system maintains different models for different stages of the pipeline.

```text
RawCandidate
      │
      ▼
FieldObservation
      │
      ▼
CanonicalProfile
      │
      ▼
Projected Output
```

### RawCandidate

Represents information extracted from a **single source**.

No merge logic or conflict resolution occurs at this stage.

---

### FieldObservation

Each extracted value becomes an individual observation.

Instead of merging whole objects, the merge engine reasons about **one field at a time**, preserving:

- source
- confidence
- extraction method

This design simplifies provenance tracking and conflict resolution.

---

### CanonicalProfile

Represents the merged, normalized, and de-duplicated candidate profile.

This is the system's internal source of truth.

No consumer receives this model directly.

---

### Projected Output

The projector transforms the canonical profile into the runtime schema defined by the configuration.

Different consumers can therefore receive completely different JSON structures without modifying the merge logic.

---

# 🧠 Merge Strategy & Conflict Resolution

Real-world candidate data rarely arrives in a clean, consistent form.

Different sources often provide:

- Conflicting names
- Different phone number formats
- Duplicate email addresses
- Incomplete skill lists
- Missing experience
- Different confidence levels

The merge engine resolves these inconsistencies using deterministic, field-specific strategies instead of simple overwrite semantics.

---

# Scalar Fields

Scalar values represent a single canonical value.

Examples include:

- Full Name
- Headline
- Years of Experience
- Location

The merge engine evaluates all observations for a field and selects the most trustworthy value using the following priority:

1. Source priority
2. Source confidence
3. Extraction confidence
4. Conflict penalty (if competing values disagree)

For example:

```text
ATS
Name = "Jashan Singh"

Resume
Name = "Jashan S."

GitHub
Name = "Jashan Singh"

↓

Canonical Name = "Jashan Singh"
```

This approach avoids arbitrary overwrites while preferring the most reliable information.

---

# List Fields

Fields containing multiple independent values are merged using union-based strategies.

Examples include:

- Email addresses
- Phone numbers
- Portfolio links

Instead of selecting a single winner, values are:

- Normalized
- Deduplicated
- Combined into a single canonical list

Example:

```text
CSV
john@gmail.com

ATS
John@gmail.com

Resume
john@gmail.com

↓

john@gmail.com
```

Duplicate values are automatically removed after normalization.

---

# Skills

Skills require a dedicated merge strategy because multiple sources may report different aliases.

Example:

```text
Resume
Python3

GitHub
python

CSV
PYTHON

↓

python
```

Each merged skill records:

- Canonical name
- Confidence score
- Contributing sources

allowing downstream consumers to understand both the resolved value and its origin.

---

# Experience & Education

Structured entities such as experience and education are merged independently.

Duplicate records are detected using identifying attributes and consolidated into a single canonical representation while preserving available metadata.

This avoids repeated entries when multiple sources describe the same employment or academic record.

---

# Provenance Tracking

Every merged field records exactly how it was produced.

Each provenance record contains:

- Winning source
- Extraction method
- Confidence
- Original raw value
- All contributing sources

Example:

```text
Field:
Email

Winner:
ATS JSON

Observed Sources:
ATS JSON
Resume
GitHub

Confidence:
0.95
```

This makes every merge decision fully explainable and auditable.

---

# Confidence Scoring

Every candidate profile receives an overall confidence score between **0.0** and **1.0**.

The score combines four independent signals:

| Signal | Description |
|---------|-------------|
| Source Reliability | Trust assigned to each source type |
| Extraction Confidence | Confidence assigned during extraction and normalization |
| Multi-Source Agreement | Additional confidence when multiple sources agree |
| Profile Completeness | Fraction of important fields successfully populated |

The confidence engine never modifies candidate data.

Its only responsibility is estimating how trustworthy the final canonical profile is.

---

# Why This Design?

Instead of treating candidate information as a collection of documents, the system treats it as a collection of **field-level observations**.

Each observation carries:

- value
- source
- confidence
- extraction method

The merge engine reasons about observations rather than entire records, enabling deterministic conflict resolution, explainable provenance, and confidence-aware merging.

---

# ⚙️ Installation & Quick Start

## Prerequisites

- Python **3.12+**
- Git

---

## Clone the Repository

```bash
git clone https://github.com/Jashan1001/candidate-data-transformer.git

cd candidate-data-transformer
```

---

## Create a Virtual Environment

### Windows

```bash
python -m venv .venv

.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv

source .venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -e .
```

or

```bash
pip install -r requirements.txt
```

---

## Verify Installation

```bash
candidate-transformer --help
```

Expected output:

```text
usage: candidate-transformer [-h]
                             [--csv CSV]
                             [--ats ATS]
                             [--github GITHUB]
                             [--resume RESUME]
                             --config CONFIG
                             --output OUTPUT
                             [--debug]
```

---

# 🚀 Running the Pipeline

The transformer accepts any combination of supported sources.

Example:

```bash
python -m transformer.cli \
    --csv input/recruiter.csv \
    --ats input/ats/sample.json \
    --resume input/resume.pdf \
    --github octocat \
    --config input/configs/default.json \
    --output output/result.json \
    --debug
```

---

# Example Pipeline Execution

```text
Loading configuration

Extracting recruiter CSV

Extracting ATS JSON

Extracting Resume

Extracting GitHub

Merging sources

Computing confidence

Validating canonical profile

Projecting output

Validating projected output

Pipeline complete
```

---

# Example Output

```json
{
  "full_name": "Jashan Singh",
  "emails": [
    "jashan@gmail.com"
  ],
  "phones": [
    "+919876543210"
  ],
  "years_experience": 3.0,
  "overall_confidence": 0.91
}
```

---

# 📁 Project Structure

```text
candidate-data-transformer/

├── input/
│   ├── ats/
│   ├── configs/
│   ├── recruiter.csv
│   └── resume.pdf
│
├── output/
│   └── result.json
│
├── src/
│   └── transformer/
│       ├── confidence/
│       ├── extractors/
│       ├── merger/
│       ├── models/
│       ├── normalizers/
│       ├── projector/
│       ├── utils/
│       ├── validator/
│       ├── cli.py
│       └── main.py
│
├── tests/
│
├── pyproject.toml
├── README.md
└── LICENSE
```

---

# 🧪 Running Tests

Execute the complete test suite:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Generate a coverage report (optional):

```bash
pytest --cov=src/transformer
```

---

# 🧹 Code Quality

Run Ruff linter:

```bash
ruff check .
```

Automatically fix simple issues:

```bash
ruff check . --fix
```

Format the project:

```bash
ruff format .
```

A clean repository should satisfy:

```bash
ruff check .

pytest
```

without warnings or failures.

---

# ⚙️ Configuration System

The output of the transformer is entirely controlled through a runtime JSON configuration.

Instead of modifying application code, users can customize the generated JSON by editing a configuration file.

The configuration controls:

- Field selection
- Field renaming
- Nested output paths
- Missing field behaviour
- Runtime normalization
- Required field validation
- Confidence inclusion
- Provenance inclusion

---

## Example Configuration

```json
{
  "fields": [
    {
      "path": "candidate.name",
      "from": "full_name"
    },
    {
      "path": "candidate.email",
      "from": "emails[0]"
    },
    {
      "path": "candidate.phone",
      "from": "phones[0]",
      "normalize": "E164"
    },
    {
      "path": "candidate.skills",
      "from": "skills"
    }
  ],
  "include_confidence": true,
  "include_provenance": true
}
```

---

## Field Mapping

Each field describes how data should be projected from the canonical profile.

| Property | Description |
|-----------|-------------|
| `path` | Destination path in the output JSON |
| `from` | Source field in the canonical profile |
| `required` | Marks the field as mandatory |
| `normalize` | Applies runtime normalization |
| `on_missing` | Controls behaviour when data is unavailable |

---

## Runtime Field Renaming

Fields can be renamed without modifying application code.

Example:

```json
{
    "path": "candidate.primary_email",
    "from": "emails[0]"
}
```

Output:

```json
{
    "candidate": {
        "primary_email": "jashan@gmail.com"
    }
}
```

---

## Nested Output

Nested JSON structures are created automatically.

Configuration:

```json
{
    "path": "contact.address.city",
    "from": "location.city"
}
```

Output:

```json
{
    "contact": {
        "address": {
            "city": "Bangalore"
        }
    }
}
```

---

## Missing Field Behaviour

The projector supports three strategies for handling missing values.

### Omit

```json
"on_missing": "omit"
```

The field is not included in the output.

---

### Null

```json
"on_missing": "null"
```

The field is included with a null value.

---

### Error

```json
"on_missing": "error"
```

Projection fails if the field cannot be resolved.

---

## Runtime Normalization

The projector can normalize values during projection, even if the canonical profile already contains normalized data.

Supported strategies include:

| Strategy | Description |
|----------|-------------|
| `E164` | Phone numbers |
| `canonical` | Skill names |
| `ISO3166` | Country codes |

This guarantees that the output contract is honoured regardless of how upstream components produced the canonical profile.

---

## Confidence & Provenance

The output configuration can optionally include additional metadata.

### Confidence

```json
"include_confidence": true
```

Example:

```json
{
    "overall_confidence": 0.91
}
```

---

### Provenance

```json
"include_provenance": true
```

Example:

```json
{
    "provenance": [
        {
            "field": "full_name",
            "source": "ats_json",
            "confidence": 0.95
        }
    ]
}
```

---

## Why Configuration-Driven Projection?

Separating the internal canonical model from the external output schema provides several advantages:

- No code changes when output requirements change
- Different consumers can receive different JSON structures
- Strong separation between business logic and presentation
- Easy integration with downstream systems
- Improved maintainability and extensibility