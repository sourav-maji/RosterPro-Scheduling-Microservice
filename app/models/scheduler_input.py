from typing import Dict, List
from pydantic import BaseModel, Field, validator, model_validator
from datetime import date


class StaffMember(BaseModel):
    id: str
    role: str


class SchedulerInput(BaseModel):
    weekStart: date

    days: List[str] = Field(..., min_items=7, max_items=7)

    shifts: Dict[str, int]
    requirements: Dict[str, Dict[str, int]]

    staff: List[StaffMember]

    unavailability: Dict[str, List[str]] = {}
    preferred_holidays: Dict[str, List[str]] = {}

    max_shifts_per_week: Dict[str, int]
    max_weekly_hours: Dict[str, int]

    min_rest_hours: int = Field(..., gt=0)

    # ---------------------------
    # FIELD VALIDATORS
    # ---------------------------

    @validator("shifts")
    def shift_hours_positive(cls, v):
        for shift, hours in v.items():
            if hours <= 0:
                raise ValueError(f"Shift '{shift}' must have positive hours")
        return v

    # ---------------------------
    # MODEL VALIDATOR (Pydantic v2)
    # ---------------------------

    @model_validator(mode="after")
    def validate_roles_and_days(self):
        staff_roles = {s.role for s in self.staff}
        staff_ids = {s.id for s in self.staff}

        # Validate requirement roles exist
        for shift, roles in self.requirements.items():
            for role in roles.keys():
                if role not in staff_roles:
                    raise ValueError(
                        f"Role '{role}' in requirements not present in staff list"
                    )

        # Validate unavailability
        for user_id, days_off in self.unavailability.items():
            if user_id not in staff_ids:
                raise ValueError(f"Unknown staff id in unavailability: {user_id}")
            for d in days_off:
                if d not in self.days:
                    raise ValueError(
                        f"Invalid day '{d}' in unavailability for {user_id}"
                    )

        return self
