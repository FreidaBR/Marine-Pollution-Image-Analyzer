"""
Actionable Recommendation Engine.
Role: Member 4 (Report, Analytics & Intelligence Engineer)

Provides tiered, evidence-based environmental recommendations according to
calculated visual pollution severity levels and hotspot indicators.
"""

from __future__ import annotations
from typing import Union, Optional
from reporting.schemas import SeverityLevel, Recommendation


RECOMMENDATIONS_MAP = {
    SeverityLevel.CLEAN: {
        "primary_action": "No visible debris detected. Continue routine baseline coastal monitoring.",
        "suggested_actions": [
            "Log imagery into the regional coastal monitoring baseline archive.",
            "Maintain standard sensor and patrol cycle without emergency intervention.",
            "Use observation as a clean reference baseline for local water-body models."
        ],
        "urgency": "Routine",
        "authority_notification_recommended": False,
    },
    SeverityLevel.LOW: {
        "primary_action": "Continue monitoring the area and record observation.",
        "suggested_actions": [
            "Log observation in coastal surveillance registry.",
            "Schedule follow-up visual check during the next regular shoreline sweep.",
            "Verify whether isolated visible debris is transient floating material or shoreline deposition."
        ],
        "urgency": "Informational",
        "authority_notification_recommended": False,
    },
    SeverityLevel.MODERATE: {
        "primary_action": "Inspect the area and consider targeted cleanup.",
        "suggested_actions": [
            "Deploy ground or drone verification patrol to evaluate debris accumulation.",
            "Assess shoreline access routes for local cleanup or citizen science volunteers.",
            "Monitor tidal drift and prevailing surface currents for downstream dispersal."
        ],
        "urgency": "Caution",
        "authority_notification_recommended": False,
    },
    SeverityLevel.HIGH: {
        "primary_action": "Prioritize field verification and cleanup assessment.",
        "suggested_actions": [
            "Dispatch municipal or coastal cleanup unit to evaluate removal requirements.",
            "Inspect nearby rivermouths, drainage outfalls, or maritime traffic for source tracking.",
            "Evaluate placement of temporary floating booms or containment barriers where viable.",
            "Notify local coastal zone management authorities of elevated accumulation."
        ],
        "urgency": "High Priority",
        "authority_notification_recommended": True,
    },
    SeverityLevel.CRITICAL: {
        "primary_action": "Immediate field verification and responsible-authority notification should be considered.",
        "suggested_actions": [
            "Issue high-priority incident notice to environmental protection & maritime authorities.",
            "Mobilize emergency coastal containment and recovery team to prevent marine habitat harm.",
            "Issue advisory for local bathing, fishing, or marine sanctuary zones in the immediate sector.",
            "Conduct drone aerial transect to map the outer boundary of the contamination cluster."
        ],
        "urgency": "Urgent Action Required",
        "authority_notification_recommended": True,
    },
}


def get_recommendations(severity: Union[SeverityLevel, str]) -> Recommendation:
    """
    Returns structured recommendations and operational guidance based on visual severity level.
    """
    if isinstance(severity, str):
        try:
            sev_enum = SeverityLevel(severity.capitalize())
        except ValueError:
            sev_enum = SeverityLevel.LOW
    else:
        sev_enum = severity

    config = RECOMMENDATIONS_MAP.get(sev_enum, RECOMMENDATIONS_MAP[SeverityLevel.LOW])

    return Recommendation(
        level=sev_enum,
        primary_action=config["primary_action"],
        suggested_actions=config["suggested_actions"],
        urgency=config["urgency"],
        authority_notification_recommended=config["authority_notification_recommended"],
        disclaimer=(
            "Assessment is based on visible image indicators only and does not reflect laboratory chemical analysis."
        ),
    )
