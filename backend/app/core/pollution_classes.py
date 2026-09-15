"""Shared pollution class-name enum/list, per the frozen API contract
(docs/api-contract.md): "Class names must come from a shared enum/list."

`ai_service.labels.LABELS` takes precedence once Member 1 defines it (so the
real model's vocabulary can differ if needed); this is the fallback used by
the mock provider and defaults today.
"""

PLASTIC_DEBRIS = "plastic_debris"
OIL_SLICK = "oil_slick"
ALGAL_BLOOM = "algal_bloom"
OTHER_CONTAMINATION = "other_contamination"
CLEAN_REFERENCE = "clean_reference"

DEFAULT_CLASS_NAMES: list[str] = [
    PLASTIC_DEBRIS,
    OIL_SLICK,
    ALGAL_BLOOM,
    OTHER_CONTAMINATION,
]

# Detections of this class don't count toward severity/dominant-category —
# it represents "no obvious visible pollution" per the project brief.
NON_POLLUTION_CLASS = CLEAN_REFERENCE


def get_class_names() -> list[str]:
    try:
        from ai_service.labels import LABELS  # type: ignore[import-not-found]

        return list(LABELS)
    except Exception:
        return list(DEFAULT_CLASS_NAMES)
