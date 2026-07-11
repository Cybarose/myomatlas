"""Request and intake schemas for the reasoning agent and the /analyze route.

All clinical intake fields are optional; the agent is told to reason
conservatively and state assumptions when a field is missing. Optional is used
(not the X | None syntax) so the models evaluate on Python 3.9.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ClinicalIntake(BaseModel):
    age: Optional[int] = None
    menopausal_status: Optional[str] = None  # premenopausal | perimenopausal | postmenopausal
    bleeding_severity: Optional[str] = None  # mild | moderate | heavy
    fertility_desire: Optional[str] = None  # desired | not_desired | undecided
    risk_factors: Optional[list[str]] = None
    notes: Optional[str] = None


class AnalyzeRequest(BaseModel):
    case_id: Optional[str] = None
    measurements: Optional[dict] = None
    intake: Optional[ClinicalIntake] = None
