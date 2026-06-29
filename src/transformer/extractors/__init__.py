"""
Base extractor interface.

Every data source (CSV, ATS JSON, Resume, GitHub, Recruiter Notes)
implements this contract. The pipeline interacts with all extractors
through this common interface, making the system extensible and
source-agnostic.
"""

from abc import ABC, abstractmethod
from typing import Any

from transformer.models.core import RawCandidate


class BaseExtractor(ABC):
    """
    Abstract base class for all extractors.

    Each extractor is responsible for reading one source type and
    producing a RawCandidate object.

    Extractors should ONLY extract data.
    They must NOT normalize, merge, or calculate confidence.
    """

    @abstractmethod
    def extract(self, source_input: Any) -> RawCandidate:
        """
        Extract candidate information from a source.

        Parameters
        ----------
        source_input : Any
            Source artifact such as a file path, URL,
            JSON object, text content, or other supported input.

        Returns
        -------
        RawCandidate
            Extracted candidate information.
        """
        pass

    def safe_extract(self, source_input: Any) -> RawCandidate:
        """
        Execute extraction safely.

        If extraction fails for any reason,
        return an empty RawCandidate instead
        of crashing the pipeline.
        """
        try:
            return self.extract(source_input)
        except Exception as exc:
            print(f"[WARN] {self.__class__.__name__} failed: {exc}")
            return self._empty()

    @abstractmethod
    def _empty(self) -> RawCandidate:
        """
        Return an empty RawCandidate for graceful degradation.
        """
        pass
