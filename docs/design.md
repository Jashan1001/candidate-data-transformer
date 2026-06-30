# Multi-Source Candidate Data Transformer

**Eightfold AI Engineering Internship Assignment**

**Author:** Jashanpreet Kaur
**Email:** [jashan100106@gmail.com](mailto:jashan100106@gmail.com)

---

# 1. Objective

Recruiters often receive candidate information from multiple independent sources such as recruiter spreadsheets, Applicant Tracking Systems (ATS), GitHub profiles, and resumes. These sources frequently contain incomplete, duplicated, and conflicting information.

The objective of this project is to consolidate heterogeneous candidate data into a single canonical profile while preserving explainability. The pipeline performs extraction, normalization, conflict resolution, confidence estimation, validation, and configurable output projection using a modular ETL architecture.

The design prioritizes deterministic behavior, extensibility, maintainability, and clear separation of responsibilities.

---

# 2. System Architecture

The pipeline follows an Extract–Transform–Load (ETL) architecture where each stage performs one well-defined responsibility.

```
Candidate Sources
        │
        ▼
Extractors
        │
        ▼
Normalization
        │
        ▼
Merge Engine
        │
        ▼
Confidence Engine
        │
        ▼
Canonical Profile Validation
        │
        ▼
Projector
        │
        ▼
Output Validation
        │
        ▼
Final JSON
```

Each stage communicates through explicit domain models rather than source-specific representations, allowing components to evolve independently.

---

# 3. Design Decisions

## Independent Extractors

Each supported source is implemented as an isolated extractor responsible only for understanding its own input format.

Current extractors include:

* Recruiter CSV
* ATS JSON
* GitHub
* Resume (PDF / DOCX)

Every extractor produces the same `RawCandidate` model and has no knowledge of normalization, merge logic, confidence scoring, or output projection.

This follows the Single Responsibility Principle and allows new sources to be added without modifying the existing pipeline.

---

## Canonical Domain Model

All downstream components operate on a common `CanonicalProfile` instead of source-specific formats.

This abstraction removes coupling between pipeline stages and provides a stable contract for merging, validation, confidence scoring, and projection.

---

## Field-Level Processing

Instead of merging complete candidate records, the system treats every extracted value as an independent field observation.

Each observation stores:

* Value
* Source
* Extraction confidence
* Extraction metadata

This enables field-specific merge strategies, provenance tracking, and deterministic conflict resolution.

---

## Normalization Before Merge

Normalization is intentionally performed before conflict resolution.

Equivalent values such as phone numbers, skills, email addresses, and locations are first converted into canonical representations, ensuring merge decisions compare standardized values rather than formatting differences.

Centralizing normalization also prevents duplicate implementations across extractors.

---

# 4. Canonical Schema

The internal canonical model closely follows the assignment specification.

Major fields include:

* Candidate ID
* Full Name
* Emails
* Phone Numbers
* Structured Location
* Links
* Headline
* Years of Experience
* Skills
* Experience
* Education
* Provenance
* Overall Confidence

Normalization rules include:

| Field         | Normalization               |
| ------------- | --------------------------- |
| Phone Numbers | E.164 (`phonenumbers`)      |
| Skills        | Canonical aliases           |
| Email         | Lowercase + validation      |
| Country       | ISO-3166 Alpha-2            |
| Dates         | Standardized representation |

---

# 5. Merge Strategy

Different categories of candidate data require different merge strategies.

## Scalar Fields

Fields such as:

* Full Name
* Headline
* Years of Experience
* Location

are resolved using deterministic conflict resolution based on:

* Source priority
* Extraction confidence
* Normalization success

Source priority is:

```
ATS JSON
    ↓
Recruiter CSV
    ↓
Resume
    ↓
GitHub
    ↓
Recruiter Notes
```

Structured employer-maintained systems are considered more reliable than self-reported information.

---

## Collection Fields

Collection fields including:

* Emails
* Phone Numbers
* Skills

are merged using:

* Union
* Deduplication
* Canonical normalization

This preserves legitimate multiple values while removing duplicates.

---

## Provenance

Every resolved field records:

* Winning source
* Original observations
* Contributing sources
* Extraction confidence
* Merge metadata

This makes every merge decision transparent and auditable.

---

# 6. Confidence Estimation

Every resolved field receives a confidence estimate based on multiple independent signals.

The confidence engine considers:

* Source reliability
* Extraction confidence
* Normalization success
* Cross-source agreement
* Conflict penalties

The overall profile confidence is computed from the confidence of populated fields.

The confidence engine evaluates reliability only; it never modifies candidate data.

---

# 7. Configuration-Driven Projection

The pipeline maintains a stable internal `CanonicalProfile`.

External consumers never access this model directly.

Instead, the `Projector` transforms the canonical profile into the JSON schema requested through a runtime `OutputConfig`.

Supported capabilities include:

* Field selection
* Field renaming
* Nested output paths
* Runtime normalization
* Required field validation
* Missing-field policies
* Optional provenance
* Optional confidence

This allows multiple consumers to receive different output schemas without modifying application code.

---

# 8. Validation Strategy

Validation is intentionally performed twice.

## Canonical Validation

Verifies the internal `CanonicalProfile` before projection.

## Output Validation

Verifies that the projected JSON satisfies the runtime configuration, including required fields and expected types.

Separating these responsibilities improves diagnostics by distinguishing invalid candidate data from invalid output configurations.

---

# 9. Edge Cases

The implementation handles several common failure scenarios.

* Conflicting names, phone numbers, and experience across multiple sources.
* Phone numbers without explicit country codes.
* Malformed ATS JSON documents.
* Missing input files.
* GitHub API failures or rate limiting.
* Missing required output fields.

Whenever possible, failures are isolated to the affected source while the remaining pipeline continues processing successfully.

---

# 10. Trade-offs

Several design decisions intentionally favor predictability over complexity.

* Merge behavior is deterministic rather than heuristic.
* Candidate identity is supplied explicitly rather than inferred through fuzzy matching.
* Output schemas are configuration-driven instead of hard-coded.
* Normalization is centralized rather than duplicated across extractors.

These choices simplify testing, debugging, and explainability while keeping the architecture extensible.

---

# 11. Future Extensions

The architecture is designed to support additional functionality with minimal changes.

Potential extensions include:

* LinkedIn extractor (subject to API availability)
* Recruiter notes parser
* Additional ATS integrations
* LLM-assisted resume parsing
* Streaming ingestion
* Parallel extraction
* Batch processing

---

# 12. Scope Limitations

The following features were intentionally left outside the scope of this assignment:

* LinkedIn integration due to the absence of a public, terms-compliant API.
* Recruiter notes extractor, although the source type already exists as an extension point.
* Automatic cross-file identity resolution using fuzzy matching.
* Advanced semantic parsing for highly unstructured resumes.

These limitations were consciously chosen to prioritize deterministic behavior, modularity, and complete implementation of the supported data sources.
