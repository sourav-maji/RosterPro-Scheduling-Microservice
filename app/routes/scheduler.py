from fastapi import APIRouter, Header, HTTPException
from app.config import settings
from app.models.scheduler_input import SchedulerInput
from app.engine.solver import solve_weekly_schedule
import traceback

router = APIRouter()

@router.post("/weekly")
def generate_weekly_schedule(
    payload: SchedulerInput,
    x_scheduler_key: str = Header(None)
):
    try:
        # 🔐 Service-to-service auth
        if x_scheduler_key != settings.SCHEDULER_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")

        result = solve_weekly_schedule(
            payload=payload,
            max_time=settings.SOLVER_MAX_TIME
        )

        return result

    except Exception as e:
        print("🔥 SCHEDULER ERROR 🔥")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Scheduler failed: {str(e)}"
        )
