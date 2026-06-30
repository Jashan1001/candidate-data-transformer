"""
Command Line Interface for Candidate Data Transformer.
"""

from __future__ import annotations

import argparse
import json

from transformer.main import CandidateTransformer
from transformer.models.config import OutputConfig
from transformer.utils.helpers import ensure_parent
from transformer.utils.logger import configure_root, get_logger

log = get_logger(__name__)


def load_config(path: str) -> OutputConfig:
    """
    Load runtime projection configuration from JSON.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return OutputConfig.model_validate(data)


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        prog="candidate-transformer",
        description="Multi-Source Candidate Data Transformer",
    )

    parser.add_argument(
        "--csv",
        help="Recruiter CSV file",
    )

    parser.add_argument(
        "--ats",
        help="ATS JSON file",
    )

    parser.add_argument(
        "--github",
        help="GitHub username or profile URL",
    )

    parser.add_argument(
        "--resume",
        help="Resume file (PDF, DOCX, or TXT)",
    )

    parser.add_argument(
        "--config",
        required=True,
        help="Projection configuration JSON",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON path",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    return parser


def main() -> None:

    parser = build_parser()
    args = parser.parse_args()

    configure_root(debug=args.debug)

    log.info("Loading configuration")

    config = load_config(args.config)

    import sys

    transformer = CandidateTransformer()

    try:
        result = transformer.run(
            recruiter_csv=args.csv,
            ats_json=args.ats,
            github=args.github,
            resume=args.resume,
            config=config,
        )
    except ValueError as exc:
        log.error("Transformation failed", error=str(exc))
        print(f"✗ Error: {exc}", file=sys.stderr)
        sys.exit(1)

    output_path = ensure_parent(args.output)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False,
        )

    log.info(
        "Transformation complete",
        output=str(output_path),
    )


if __name__ == "__main__":
    main()