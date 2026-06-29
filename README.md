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