"""Pydantic request models."""

from pydantic import BaseModel, Field


class AnalyzeParams(BaseModel):
    """Query parameters for POST /analyze."""

    permission_to_record: bool = Field(
        default=False,
        description="If true, encrypted payload + image written to data/records/.",
    )
