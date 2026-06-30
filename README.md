# Multi-Source Candidate Data Transformer

> A modular, production-inspired ETL pipeline that consolidates candidate information from multiple heterogeneous sources into a single canonical profile with deterministic conflict resolution, configurable output projection, field-level provenance, and confidence scoring.

<p align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Pydantic](https://img.shields.io/badge/Pydantic-2.x-E92063)
![Pytest](https://img.shields.io/badge/Pytest-108%20Tests-0A9EDC)
![Ruff](https://img.shields.io/badge/Ruff-Lint%20%26%20Format-black)
![License](https://img.shields.io/badge/License-MIT-green)

</p>

> **Built as part of the Eightfold AI Engineering Internship Assignment (July–December 2026).**

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the pipeline (default schema, 2 structured sources)
python -m transformer.cli \
  --csv input/recruiter.csv \
  --ats input/ats/sample.json \
  --config input/configs/default.json \
  --output output/result_default.json

# 3. Run with a structured + unstructured source and a custom output schema
python -m transformer.cli \
  --csv input/recruiter.csv \
  --resume input/resume/sample_resume.txt \
  --config input/configs/custom.json \
  --output output/result_custom.json

# 4. Run the test suite
PYTHONPATH=src pytest tests/ -v
```

All flags: `--csv`, `--ats`, `--github`, `--resume`, `--config` (required), `--output` (required), `--debug`.
Pre-generated outputs for both configs (and a required-field error demo) are committed under `output/`.

---

## Overview

Recruiters and hiring platforms rarely receive candidate information from a single source. A candidate's profile may be distributed across recruiter spreadsheets, Applicant Tracking Systems (ATS), GitHub profiles, resumes, and other external systems. These sources often contain incomplete, duplicated, or conflicting information.

Simply combining records is insufficient. Before the data can be consumed reliably, it must be standardized, validated, merged using deterministic rules, and transformed into a consistent representation while preserving the origin of every decision.

Candidate Data Transformer addresses this problem through a modular ETL pipeline that:

* Extracts candidate data from heterogeneous sources into a common domain model.
* Normalizes inconsistent representations such as names, phone numbers, email addresses, locations, skills, and dates.
* Resolves conflicting observations using field-specific merge strategies based on source reliability and extraction confidence.
* Produces a single canonical candidate profile that serves as the system's source of truth.
* Tracks complete field-level provenance to make every merge decision transparent and explainable.
* Computes confidence scores that estimate the reliability of both individual fields and the overall profile.
* Projects the canonical profile into configurable JSON without modifying application code.

The project emphasizes clean architecture, explicit data contracts, deterministic behavior, and extensibility. Each stage of the pipeline has a single responsibility, making it straightforward to introduce new data sources, normalization rules, merge strategies, or output schemas without affecting the rest of the system.

## Problem Statement

Modern hiring workflows rely on information collected from multiple independent systems. A single candidate may appear in recruiter spreadsheets, Applicant Tracking Systems (ATS), resumes, GitHub profiles, internal databases, and other external sources. Each source captures different aspects of the candidate and often represents the same information in inconsistent ways.

For example, one source may report a candidate as **"Priya Mehra"**, another as **"Priya Mehraa"**, while a GitHub profile might expose a completely different display name. Phone numbers may appear with or without country codes, skills may be written using different aliases, and experience or education records may overlap without matching exactly.

These inconsistencies create several challenges:

* Duplicate information represented in different formats.
* Conflicting values reported by different sources.
* Missing fields in otherwise reliable records.
* Difficulty determining which source should be trusted.
* Limited visibility into how the final profile was constructed.

A naïve approach that simply overwrites fields or concatenates records produces inconsistent and difficult-to-audit results. Such pipelines cannot explain why a particular value was selected, which source contributed it, or how reliable the final profile is.

This project approaches the problem as an **Extract–Transform–Load (ETL)** pipeline rather than a document aggregation task.

Instead of treating each source as a complete candidate record, the pipeline models candidate information as a collection of **field-level observations**. Every observation preserves its value, source, extraction confidence, and metadata. These observations are then normalized, evaluated using deterministic merge strategies, and consolidated into a single canonical profile.

The result is a transparent, explainable, and extensible transformation pipeline that produces consistent candidate profiles while preserving the provenance of every decision made during the merge process.

## Key Features

### Multi-Source Candidate Ingestion

The pipeline accepts candidate information from multiple independent sources and converts each into a common `RawCandidate` model.

Currently supported sources include:

* 📄 Recruiter CSV
* 🗂 ATS JSON (Greenhouse, Lever, Generic)
* 💻 GitHub Profile
* 📑 Resume (PDF / DOCX)

Each source is implemented as an independent extractor with a shared interface. New sources can be added by implementing the extractor contract without modifying the rest of the pipeline.

---

### Canonical Domain Model

Rather than allowing downstream components to understand every input format, all extracted data is transformed into a common domain model.

This separation isolates parsing logic from business logic and allows the merge engine, validator, and projector to operate independently of the original data source.

---

### Data Normalization

Before conflict resolution, candidate information is normalized into consistent representations.

Current normalization includes:

* Email address validation and canonicalization
* Phone number normalization to E.164 format
* Candidate name cleanup
* Skill alias normalization
* Date standardization
* Location normalization

Normalizing data before merging ensures equivalent values can be compared reliably regardless of how they were represented in the original source.

---

### Deterministic Merge Engine

Candidate information is merged using field-specific strategies instead of simple overwrite semantics.

Depending on the field type, the merge engine can:

* Select the most reliable scalar value.
* Union and deduplicate collection fields.
* Merge structured entities such as skills, education, and work experience.
* Preserve every contributing observation for provenance tracking.

Merge decisions are deterministic, making repeated executions with identical inputs produce identical outputs.

---

### Field-Level Provenance

Every resolved field records how it was produced.

For each merged value, the pipeline tracks:

* Winning source
* Contributing sources
* Original observed values
* Extraction confidence
* Merge metadata

This enables complete traceability and allows downstream systems to understand why a particular value was selected.

---

### Confidence Scoring

Each canonical profile receives an overall confidence score derived from multiple signals, including source reliability, extraction confidence, agreement across sources, and profile completeness.

Confidence scores provide consumers with an estimate of how trustworthy the merged profile is without altering the underlying candidate data.

---

### Configuration-Driven Projection

The internal canonical profile remains stable regardless of how consumers wish to receive data.

A runtime `OutputConfig` controls:

* Field selection
* Field renaming
* Nested output paths
* Runtime normalization
* Required field validation
* Optional confidence and provenance output

Different consumers can therefore receive different JSON schemas from the same canonical profile without changing application code.

---

### Validation at Multiple Pipeline Stages

Validation is performed both before and after projection.

The canonical profile is validated to ensure internal consistency, while the projected output is validated against the configured output contract.

Separating these validation stages helps detect both data-quality issues and configuration errors independently.

---

### Comprehensive Test Coverage

The project includes an extensive automated test suite covering:

* Individual extractors
* Merge strategies
* Normalization logic
* Confidence scoring
* Validation
* Projection
* End-to-end pipeline behavior

This modular testing approach allows each component to evolve independently while maintaining confidence in the overall pipeline.

# System Architecture

The Candidate Data Transformer follows a modular **Extract–Transform–Load (ETL)** architecture. Each stage is responsible for a single step in the transformation pipeline and communicates with the next stage through explicit domain models rather than source-specific data structures.

This separation of responsibilities keeps the pipeline deterministic, testable, and easy to extend. New data sources, merge strategies, or output formats can be introduced without requiring changes across unrelated components.

```text
                    Candidate Data Sources

       Recruiter CSV      ATS JSON      GitHub      Resume
             │               │             │            │
             └───────────────┼─────────────┼────────────┘
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
                   Output Validation
                             │
                             ▼
                        Final JSON
```

The pipeline transforms heterogeneous candidate data into a single canonical representation while preserving the provenance of every resolved field. Each stage performs one well-defined responsibility and passes its output to the next stage through strongly typed models.

---

## Pipeline Walkthrough

The transformation process consists of seven sequential stages.

### 1. Extraction

Each supported source is processed by its corresponding extractor. The extractor understands only its own input format and converts it into a common `RawCandidate` model.

At this stage, no normalization, conflict resolution, or business logic is performed.

---

### 2. Merge

The merge engine combines observations from every `RawCandidate` into a single `CanonicalProfile`.

Instead of merging complete records, it evaluates candidate information at the field level. Different merge strategies are applied depending on the type of data being resolved.

---

### 3. Confidence Scoring

Once the canonical profile has been constructed, the confidence engine estimates the reliability of each resolved field and computes an overall profile confidence.

The confidence engine never modifies candidate data—it only evaluates how trustworthy the merged result is.

---

### 4. Canonical Profile Validation

Before exposing data to downstream consumers, the canonical profile is validated to ensure required fields, data types, and internal consistency satisfy the application's domain model.

---

### 5. Projection

The projector transforms the canonical profile into the output schema requested by the runtime `OutputConfig`.

This allows different consumers to receive different JSON structures while sharing the same internal representation.

---

### 6. Output Validation

The projected JSON is validated against the configured output contract to ensure required fields, field mappings, and runtime transformations have produced a valid result.

Separating this validation from canonical profile validation allows configuration errors to be detected independently from data quality issues.

---

### 7. Final Output

After successful validation, the pipeline produces the final JSON document containing the transformed candidate profile along with any optional metadata such as confidence scores or provenance.

---

# Internal Data Flow

The pipeline intentionally maintains different models for different stages of processing rather than relying on a single mutable object throughout the application.

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

Represents all information extracted from a single source.

Every extractor produces the same model regardless of whether the original input was a CSV file, ATS export, GitHub profile, or resume.

---

### FieldObservation

Each individual field extracted from a source becomes a `FieldObservation`.

A field observation preserves:

* observed value
* source
* extraction confidence
* extraction metadata

Treating fields as independent observations enables deterministic conflict resolution, provenance tracking, and confidence-aware merging.

---

### CanonicalProfile

The merge engine consolidates all field observations into a single canonical representation.

The `CanonicalProfile` acts as the system's internal source of truth and is intentionally independent of any external consumer or output schema.

---

### Projected Output

The projector converts the canonical profile into the JSON structure defined by the runtime configuration.

By separating the internal domain model from the exported representation, the same pipeline can satisfy multiple downstream systems without modifying merge logic or business rules.

# Core Design Decisions

The implementation is organized around a set of architectural decisions intended to keep the pipeline modular, deterministic, and easy to extend. Rather than optimizing for a specific input format or output schema, the system separates responsibilities into independent stages connected through explicit domain models.

The following sections describe the reasoning behind the most important design decisions.

---

## Independent Extractors

Each supported source is implemented as an independent extractor responsible only for understanding its own input format.

Every extractor converts its input into the common `RawCandidate` model and has no knowledge of normalization, merge logic, validation, or output projection.

This separation follows the **Single Responsibility Principle** and keeps source-specific parsing isolated from the rest of the application.

As a result:

* Bugs in one extractor cannot affect another.
* New data sources can be introduced without modifying the merge engine.
* Business logic remains independent of external data formats.

For example, supporting a future LinkedIn export would only require implementing another extractor that produces a `RawCandidate`.

---

## Canonical Domain Model

All downstream components operate on a shared domain model instead of source-specific data structures.

Without this abstraction, every component would need to understand multiple external formats, creating unnecessary coupling between modules.

Using a canonical representation provides a stable contract between pipeline stages and allows the merge engine, validator, confidence engine, and projector to remain completely independent of how the data was originally collected.

---

## Normalization Before Merge

Normalization is performed before conflict resolution rather than inside individual extractors or the merge engine.

This ensures that equivalent values are compared in a consistent representation.

For example, the following values all represent the same phone number:

* `9876543210`
* `+91 98765 43210`
* `(98765) 43210`

By normalizing them before merging, the merge engine compares canonical values instead of formatting differences.

Centralizing normalization also avoids duplicate implementations across multiple extractors and guarantees consistent behaviour regardless of the input source.

---

## Field-Level Observations

Instead of merging complete candidate records, the pipeline reasons about individual field observations.

Each observation preserves:

* value
* source
* extraction confidence
* extraction metadata

This design enables field-specific conflict resolution, fine-grained provenance tracking, and independent confidence estimation for every resolved value.

It also allows different merge strategies to be applied to different field types without affecting unrelated data.

---

## Deterministic Conflict Resolution

Merge decisions are deterministic.

Given the same inputs and configuration, the pipeline will always produce the same canonical profile.

Rather than depending on input order, merge decisions are based on explicit rules such as source priority, extraction confidence, normalization results, and field-specific merge strategies.

Deterministic behaviour makes the pipeline easier to test, debug, and reason about while improving reproducibility across environments.

---

## Separation of Internal and External Models

The internal `CanonicalProfile` represents the application's source of truth.

External consumers never interact with this model directly.

Instead, the projector transforms the canonical profile into the JSON structure requested through the runtime configuration.

Keeping the internal model independent from the output schema provides several benefits:

* Internal business logic remains stable.
* Different consumers can receive different JSON structures.
* Output requirements can evolve without affecting merge logic.

This separation follows a common DTO (Data Transfer Object) projection pattern used in production systems.

---

## Two-Stage Validation

Validation is intentionally performed twice.

The first validation stage verifies that the canonical profile satisfies the application's internal data model.

The second validation stage verifies that the projected JSON satisfies the runtime output contract.

Although both stages perform validation, they protect different boundaries within the system.

Separating them makes it possible to distinguish between invalid candidate data and invalid output configurations, resulting in clearer error reporting and easier debugging.

---

## Configuration Over Code

Output generation is controlled through configuration rather than hard-coded mappings.

Instead of modifying application logic whenever a downstream consumer requires a different schema, the projector reads an `OutputConfig` describing field mappings, renaming rules, normalization requirements, and validation behaviour.

This approach keeps business logic independent from presentation concerns and allows the same canonical profile to serve multiple consumers without code changes.

---

## Graceful Degradation

The pipeline is designed to tolerate partial failures whenever possible.

If one extractor fails because of malformed input or an unavailable external service, the remaining sources continue to be processed.

Instead of terminating the entire pipeline, the system produces the best canonical profile that can be constructed from the successfully extracted data.

This behaviour improves reliability in real-world environments where external data sources cannot always be assumed to be available or well-formed.

# Merge Strategy & Conflict Resolution

Candidate information collected from multiple sources is rarely consistent. Different systems may report conflicting names, duplicate contact information, overlapping employment history, or different representations of the same skill.

The merge engine resolves these inconsistencies by applying **field-specific merge strategies** rather than treating every field identically.

Instead of merging entire candidate records, the engine evaluates individual field observations and selects the most appropriate strategy for each type of data.

This approach produces deterministic, explainable, and extensible merge behaviour.

---

## Field-Level Merge Philosophy

Every value extracted from an external source becomes an independent observation containing:

* Observed value
* Source
* Extraction confidence
* Supporting metadata

The merge engine evaluates these observations one field at a time instead of comparing complete candidate records.

This allows each field to be resolved using the strategy that best matches its semantics while preserving complete provenance.

---

## Scalar Fields

Scalar fields represent values where only one canonical value should exist.

Examples include:

* Full Name
* Headline
* Years of Experience
* Current Location

When multiple observations exist, the merge engine selects the most reliable value using a deterministic evaluation process based on:

* Source priority
* Extraction confidence
* Normalization results
* Conflict resolution rules

### Example

| Source   | Observed Value |
| -------- | -------------- |
| ATS JSON | Priya Mehra    |
| Resume   | Priya Mehraa   |
| GitHub   | Priya Mehra    |

↓

**Canonical Value**

```text
Priya Mehra
```

The chosen value is recorded together with its provenance, allowing downstream consumers to understand both the selected value and the reasoning behind it.

---

## Collection Fields

Some candidate attributes naturally contain multiple valid values.

Examples include:

* Email addresses
* Phone numbers
* Portfolio URLs
* Social profiles

Selecting a single winner would discard useful information.

Instead, the merge engine:

1. Normalizes values.
2. Removes duplicates.
3. Produces the union of all unique observations.
4. Preserves provenance for every retained value.

### Example

| Source        | Email                                                     |
| ------------- | --------------------------------------------------------- |
| Recruiter CSV | [priya.mehra@example.com](mailto:priya.mehra@example.com) |
| ATS JSON      | [Priya.Mehra@example.com](mailto:Priya.Mehra@example.com) |
| Resume        | [priya.mehra@example.com](mailto:priya.mehra@example.com) |

↓

```text
[
  "priya.mehra@example.com"
]
```

Normalization allows equivalent values to be identified even when formatting differs across sources.

---

## Skills

Skills require specialized handling because the same technology is often represented using different aliases.

Examples include:

* Python
* python
* Python 3
* PYTHON

After normalization, equivalent skills are merged into a single canonical representation while retaining information about every contributing source.

This avoids duplicate entries without losing information about where each observation originated.

---

## Experience and Education

Experience and education are structured entities rather than simple scalar values.

Multiple sources may describe the same employment or academic record while providing different levels of detail.

The merge engine identifies overlapping records, consolidates available information, and produces a single canonical representation whenever possible.

This reduces duplication while preserving useful metadata contributed by different sources.

---

## Provenance Tracking

Every merge decision records how the canonical value was produced.

For each resolved field, provenance includes:

* Selected value
* Winning source
* Contributing sources
* Original observations
* Extraction confidence
* Merge metadata

This makes every merge decision transparent and supports auditing, debugging, and downstream analysis.

Rather than acting as a simple log, provenance forms an integral part of the merge process by documenting how the canonical profile was constructed.

---

## Why Different Strategies?

Not every field should be merged in the same way.

For example:

* A candidate may legitimately have multiple email addresses.
* A candidate should have only one canonical full name.
* Skills should be deduplicated rather than overwritten.
* Experience records should be consolidated rather than concatenated.

Applying a single generic merge algorithm would either discard useful information or introduce unnecessary duplication.

Field-specific strategies allow the merge engine to preserve the semantics of each type of data while remaining deterministic and explainable.

---

## Design Trade-offs

The merge engine intentionally favors deterministic behaviour over heuristic or probabilistic matching.

This approach offers several advantages:

* Predictable and reproducible results.
* Easier debugging and testing.
* Transparent decision-making.
* Straightforward provenance tracking.

The trade-off is that some complex real-world scenarios—such as fuzzy entity matching across unrelated records—are intentionally left outside the scope of this project in favor of keeping merge behaviour explicit and explainable.

# Configuration-Driven Output Projection

The pipeline separates its internal domain model from the JSON returned to downstream consumers.

Once the merge process produces a `CanonicalProfile`, that model becomes the system's source of truth. It remains stable regardless of how different consumers expect to receive candidate data.

Instead of embedding output mappings directly into application code, the pipeline uses a runtime `OutputConfig` to describe how the canonical profile should be transformed into the final JSON document.

This separation allows the same canonical profile to be projected into multiple output schemas without modifying business logic.

---

## Why Configuration-Driven Projection?

Different consumers often require different representations of the same candidate profile.

For example:

* A recruiter dashboard may require only basic contact information.
* An ATS integration may require nested objects following its own schema.
* An analytics system may need confidence scores and provenance metadata.
* Another downstream service may expect completely different field names.

Without a configurable projection layer, every new output format would require application code changes.

Instead, the pipeline keeps the canonical model stable and delegates output customization to configuration.

---

## What Can Be Configured?

The runtime configuration controls how the final JSON is produced.

Supported capabilities include:

* Field selection
* Field renaming
* Nested output paths
* Runtime normalization
* Required field validation
* Missing field behavior
* Optional confidence metadata
* Optional provenance metadata

Because these rules are defined externally, the same transformation pipeline can satisfy multiple consumers using different configurations.

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
      "path": "candidate.primary_email",
      "from": "emails[0]"
    },
    {
      "path": "candidate.primary_phone",
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

Each entry in the configuration describes how a value should be projected from the canonical profile into the output document.

| Property     | Description                                     |
| ------------ | ----------------------------------------------- |
| `path`       | Destination path in the output JSON             |
| `from`       | Source field in the canonical profile           |
| `required`   | Marks the field as mandatory                    |
| `normalize`  | Applies runtime normalization during projection |
| `on_missing` | Defines how missing values should be handled    |

---

## Field Renaming

Field names can be changed without modifying the application's business logic.

For example:

```json
{
    "path": "candidate.primary_email",
    "from": "emails[0]"
}
```

Produces:

```json
{
    "candidate": {
        "primary_email": "priya.mehra@example.com"
    }
}
```

---

## Nested Output Structures

The projector automatically creates nested objects based on the configured destination path.

Configuration:

```json
{
    "path": "candidate.contact.city",
    "from": "location.city"
}
```

Produces:

```json
{
    "candidate": {
        "contact": {
            "city": "Bengaluru"
        }
    }
}
```

The canonical model remains unchanged while different output hierarchies can be generated through configuration alone.

---

## Handling Missing Values

Different consumers may expect different behavior when data is unavailable.

The projector supports configurable strategies for missing fields.

| Strategy | Behavior                                         |
| -------- | ------------------------------------------------ |
| `omit`   | Excludes the field from the output               |
| `null`   | Includes the field with a `null` value           |
| `error`  | Fails projection if the field cannot be resolved |

This allows downstream contracts to define their own tolerance for incomplete data.

---

## Runtime Normalization

Although candidate data is normalized during the transformation pipeline, the projector can optionally apply additional normalization while generating the final output.

Examples include:

* Phone numbers in E.164 format
* Canonical skill names
* ISO country codes

This ensures the exported JSON satisfies the expectations of each downstream consumer without modifying the canonical profile.

---

## Confidence and Provenance

The output configuration can optionally expose additional metadata.

### Confidence

```json
{
    "overall_confidence": 0.93
}
```

### Provenance

```json
{
    "provenance": [
        {
            "field": "full_name",
            "winning_source": "ATS JSON",
            "confidence": 0.95
        }
    ]
}
```

Consumers that require explainability can include this metadata, while others can omit it entirely.

---

## Design Benefits

Separating the internal domain model from the projected output provides several architectural advantages:

* Business logic remains independent of presentation requirements.
* New output schemas can be introduced without changing application code.
* Multiple consumers can receive different JSON structures from the same canonical profile.
* The internal data model remains stable even as external contracts evolve.
* Configuration changes are isolated from merge and transformation logic.

This separation follows a common projection (DTO) pattern used in production systems, where a stable domain model serves multiple downstream interfaces with different data contracts.

# Project Structure

The repository is organized around the major stages of the transformation pipeline. Each package owns a single responsibility and communicates with other components through explicit domain models rather than direct implementation dependencies.

```text
candidate-data-transformer/
│
├── input/
│   ├── ats/
│   ├── configs/
│   ├── recruiter.csv
│   └── resumes/
│
├── output/
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
├── docs/
│
├── pyproject.toml
├── README.md
└── LICENSE
```

The project follows a modular package structure where each component is responsible for a distinct stage of the pipeline.

---

## `extractors/`

Contains one extractor implementation for each supported data source.

Current implementations include:

* Recruiter CSV
* ATS JSON
* GitHub
* Resume (PDF / DOCX)

Every extractor implements the same interface and produces a `RawCandidate`, ensuring the rest of the pipeline remains independent of input formats.

---

## `models/`

Defines the shared domain models used throughout the application.

Key models include:

* `RawCandidate`
* `FieldObservation`
* `CanonicalProfile`
* `OutputConfig`

These models act as explicit contracts between pipeline stages, reducing coupling and improving type safety.

---

## `normalizers/`

Contains reusable normalization utilities responsible for converting inconsistent input into canonical representations.

Examples include:

* Email normalization
* Phone normalization
* Skill normalization
* Name normalization
* Date normalization
* Location normalization

Centralizing normalization avoids duplicate implementations across extractors and guarantees consistent behaviour throughout the pipeline.

---

## `merger/`

Implements the core business logic of the application.

Responsibilities include:

* Field-level conflict resolution
* Merge strategies
* Provenance generation
* Canonical profile construction

The merger operates entirely on normalized observations and remains independent of input formats.

---

## `confidence/`

Computes confidence estimates for resolved fields and the overall candidate profile.

This module evaluates the reliability of merged data without modifying the canonical profile itself.

Separating confidence scoring from merge logic keeps each component focused on a single responsibility.

---

## `validator/`

Provides validation at two different stages of the pipeline.

* Canonical profile validation
* Projected output validation

Separating these concerns makes configuration errors easier to distinguish from invalid candidate data.

---

## `projector/`

Transforms the internal `CanonicalProfile` into the JSON schema described by the runtime configuration.

This layer isolates presentation concerns from business logic and enables multiple output schemas without changing application code.

---

## `utils/`

Contains shared helper functions and utilities used across multiple modules.

Keeping generic utilities separate prevents unrelated functionality from being duplicated throughout the project.

---

## `main.py`

Acts as the orchestration layer for the entire transformation pipeline.

It coordinates extraction, merging, confidence scoring, validation, projection, and output generation without embedding business logic from any individual module.

---

## `cli.py`

Provides the command-line interface for running the pipeline.

Its responsibility is limited to parsing user input, validating command-line arguments, and invoking the application entry point.

Keeping the CLI separate from the pipeline logic allows the core application to be reused by other interfaces such as REST APIs, scheduled jobs, or workflow orchestrators.

---

## `tests/`

Contains unit and integration tests covering every stage of the pipeline.

Tests are organized to validate individual modules in isolation as well as complete end-to-end execution, ensuring changes in one component do not unintentionally affect others.

---

## `docs/`

Contains supporting design documentation, architectural notes, and implementation details that complement the README.

Moving detailed design discussions into dedicated documentation keeps the README focused while still providing deeper technical context for interested readers.

---

## Why This Structure?

The repository is organized around **responsibilities rather than technologies**.

Each package owns one stage of the transformation pipeline, making the system easier to understand, test, and extend.

This organization provides several benefits:

* High cohesion within each module.
* Low coupling between pipeline stages.
* Independent testing of individual components.
* Easier onboarding for new contributors.
* Straightforward extension through new extractors, merge strategies, or output configurations.

By aligning the directory structure with the system architecture, the repository reflects the logical flow of the application rather than simply grouping files by type.

# Testing & Code Quality

Reliability is an important requirement for data transformation pipelines. Small changes in parsing, normalization, or merge logic can affect the correctness of the final candidate profile.

To reduce regression risk, the project includes automated tests covering each stage of the pipeline independently, together with end-to-end validation of the complete transformation workflow.

---

## Test Strategy

The test suite is organized around the major responsibilities of the system rather than individual files.

Coverage includes:

* Extractors
* Data normalization
* Merge strategies
* Provenance generation
* Confidence scoring
* Validation
* Output projection
* End-to-end pipeline execution

Testing components independently makes it easier to identify regressions while ensuring that each module behaves correctly in isolation.

---

## Unit Testing

Individual modules are tested independently to verify their expected behaviour.

Examples include:

* Extractors correctly parse supported input formats.
* Phone numbers are normalized into E.164 format.
* Email addresses are canonicalized consistently.
* Duplicate skills are merged correctly.
* Merge strategies resolve conflicting observations deterministically.
* Validators reject invalid data while accepting valid profiles.

By testing modules independently, implementation changes can be made with confidence without affecting unrelated parts of the pipeline.

---

## Integration Testing

In addition to unit tests, the project includes end-to-end tests that execute the complete transformation pipeline.

These tests verify that multiple components work together correctly, from data extraction through projection and final output validation.

Typical scenarios include:

* Combining multiple heterogeneous sources.
* Handling partially missing candidate information.
* Processing malformed or incomplete inputs.
* Producing configurable output using different projection configurations.

Integration tests ensure that interactions between modules remain correct as the project evolves.

---

## Deterministic Behaviour

One of the primary goals of the merge engine is deterministic output.

Given identical inputs and configuration, the pipeline should always produce the same canonical profile.

The test suite verifies this behaviour by ensuring merge decisions remain consistent across repeated executions.

Deterministic behaviour simplifies debugging, improves reproducibility, and increases confidence in automated processing pipelines.

---

## Error Handling

The pipeline is designed to fail gracefully whenever possible.

Tests cover scenarios such as:

* Invalid JSON documents.
* Missing input fields.
* Unsupported file formats.
* Malformed candidate data.
* Partial source failures.

Instead of terminating the entire pipeline, recoverable failures are isolated so that remaining sources can still contribute to the final candidate profile.

---

## Code Quality

The project uses modern Python development tools to maintain readability and consistency.

### Pytest

`pytest` is used for automated unit and integration testing.

Run the complete test suite:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

---

### Ruff

Ruff is used for linting and code formatting.

Check for linting issues:

```bash
ruff check .
```

Automatically fix supported issues:

```bash
ruff check . --fix
```

Format the codebase:

```bash
ruff format .
```

---

## Continuous Verification

Before submission, the project satisfies the following quality checks:

* All automated tests pass successfully.
* Ruff reports no linting issues.
* Source code is consistently formatted.
* The complete pipeline executes successfully using the provided sample inputs.

These checks help ensure that the repository remains maintainable, predictable, and easy to extend as new functionality is added.

# Engineering Principles

The project is organized around a set of software engineering principles that prioritize maintainability, extensibility, and predictable behaviour. These principles influenced both the architecture and the implementation of the pipeline.

---

## Single Responsibility Principle (SRP)

Each module is responsible for one well-defined concern.

For example:

* **Extractors** only read external data sources.
* **Normalizers** only standardize data.
* **Merge Engine** only resolves conflicting observations.
* **Confidence Engine** only estimates profile reliability.
* **Validator** only verifies data contracts.
* **Projector** only transforms the canonical profile into the requested output schema.

Keeping responsibilities separate reduces coupling and allows individual components to evolve independently.

---

## Separation of Concerns

The pipeline separates parsing, transformation, validation, and presentation into independent stages.

Rather than combining all processing into a single workflow, each stage communicates through explicit domain models.

This makes the system easier to reason about, simplifies testing, and prevents implementation details from leaking across module boundaries.

---

## Explicit Domain Models

Instead of passing dictionaries between components, the pipeline defines explicit models such as:

* `RawCandidate`
* `FieldObservation`
* `CanonicalProfile`
* `OutputConfig`

These models establish clear contracts between pipeline stages, improving readability, validation, and type safety while reducing ambiguity throughout the application.

---

## Configuration Over Code

Business logic remains independent of consumer-specific output requirements.

Rather than modifying application code whenever a new output schema is required, the projector reads a runtime configuration describing field mappings, renaming rules, normalization behaviour, and validation requirements.

This keeps the transformation pipeline stable while allowing output contracts to evolve independently.

---

## Deterministic Processing

Given the same inputs and configuration, the pipeline always produces the same output.

Merge decisions are based on explicit rules rather than execution order or non-deterministic heuristics.

Deterministic behaviour improves reproducibility, simplifies debugging, and makes automated testing significantly more reliable.

---

## Explainability

Every merge decision is accompanied by field-level provenance describing how the canonical value was produced.

Instead of exposing only the final result, the pipeline preserves:

* Selected value
* Winning source
* Contributing sources
* Extraction confidence
* Supporting metadata

This makes transformation decisions transparent and supports auditing, debugging, and downstream analysis.

---

## Graceful Degradation

External data sources cannot always be assumed to be available or well-formed.

Whenever possible, failures are isolated to the affected source while the remaining pipeline continues processing successfully.

This allows the system to produce the best possible canonical profile instead of failing the entire transformation because of a single malformed input.

---

## Extensibility

The architecture is designed so that new functionality can be introduced with minimal impact on existing components.

Examples include:

* Adding a new extractor without modifying the merge engine.
* Introducing additional normalization rules independently.
* Supporting new merge strategies for future field types.
* Defining new output schemas through configuration rather than code.

This modular organization reduces the cost of future enhancements and encourages incremental development.

---

## Testability

Each stage of the pipeline can be tested independently because responsibilities are clearly separated and components communicate through explicit interfaces.

This enables:

* Focused unit tests for individual modules.
* Integration tests for complete pipeline execution.
* Faster debugging when regressions occur.
* Greater confidence when introducing new functionality.

Designing for testability improves long-term maintainability and helps ensure that changes remain isolated.

---

## Why These Principles Matter

The primary objective of the project is not simply to transform candidate data, but to do so in a way that remains understandable, maintainable, and adaptable as requirements evolve.

Applying these principles results in a codebase that is easier to extend, easier to test, and easier to reason about than a monolithic implementation where parsing, merging, validation, and output generation are tightly coupled.

# Reliability & Failure Handling

Real-world data pipelines operate on information collected from multiple external systems. These systems cannot always be assumed to provide complete, valid, or consistent data.

For this reason, the Candidate Data Transformer is designed to tolerate recoverable failures whenever possible while providing clear feedback for unrecoverable errors.

The objective is not simply to detect failures, but to isolate them so that a problem in one source does not unnecessarily prevent processing of all remaining data.

---

## Graceful Degradation

Each supported source is processed independently.

If one extractor encounters malformed input, an unsupported file, or an external service failure, the remaining sources continue through the pipeline.

Rather than terminating the entire transformation, the pipeline constructs the best canonical profile possible from the successfully extracted data.

This approach improves availability while ensuring that isolated failures do not invalidate otherwise useful candidate information.

---

## Input Validation

Candidate information is validated at multiple stages of the pipeline.

Validation includes checks such as:

* Required configuration values
* Supported input formats
* Schema validation
* Missing mandatory fields
* Invalid data types

Invalid inputs are detected as early as possible, allowing errors to be reported close to their source.

---

## Defensive Processing

External data should never be assumed to be clean or consistent.

The pipeline therefore performs normalization and validation before business logic is applied.

Examples include:

* Canonicalizing email addresses before comparison.
* Converting phone numbers into a consistent representation.
* Standardizing dates before merge decisions.
* Cleaning candidate names before conflict resolution.

By validating and normalizing data early, downstream components can operate on predictable representations rather than handling inconsistent input repeatedly.

---

## Clear Failure Boundaries

Different categories of failures are handled independently.

Examples include:

| Failure                      | Pipeline Behaviour                                                    |
| ---------------------------- | --------------------------------------------------------------------- |
| Malformed ATS JSON           | Skip the affected source and continue processing remaining sources.   |
| Resume parsing failure       | Continue using recruiter, ATS, and GitHub data.                       |
| Missing optional fields      | Produce a partial profile when permitted by the output configuration. |
| Invalid output configuration | Stop projection and report a configuration error.                     |

Treating failures independently results in clearer diagnostics and more predictable system behaviour.

---

## Deterministic Recovery

Recoverable failures are handled consistently.

Given the same inputs and the same failure conditions, the pipeline always produces the same canonical profile and the same error reporting behaviour.

Deterministic recovery simplifies debugging, testing, and operational troubleshooting.

---

## Validation Boundaries

The pipeline validates data at two independent stages.

**Canonical Profile Validation**

Verifies that the internal domain model is complete and internally consistent before projection.

**Output Validation**

Ensures that the projected JSON satisfies the schema described by the runtime configuration.

Separating these responsibilities makes it easier to distinguish between data quality problems and configuration errors.

---

## Explainable Errors

Whenever the pipeline encounters an unrecoverable error, it reports the failure together with sufficient context to identify the affected stage.

Rather than returning generic failures, errors are associated with the component responsible for the failure, making diagnosis and debugging significantly easier.

---

## Reliability by Design

Reliability is achieved through architectural decisions rather than isolated error checks.

The combination of independent extractors, explicit validation boundaries, deterministic merge behaviour, configuration-driven projection, and graceful degradation allows the pipeline to remain predictable even when processing incomplete or inconsistent candidate data.

This approach reflects a common design principle in production ETL systems: process as much valid data as possible while making failures visible, isolated, and explainable.