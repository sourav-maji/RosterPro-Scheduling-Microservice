from fastapi import FastAPI
from app.routes.scheduler import router as scheduler_router


app = FastAPI(
    title= "SmartShift Scheduler Service",
    version= "1.0.0"
)

# Routes

app.include_router(scheduler_router, prefix= "/schedule")

@app.get("/health")
def health():
    return {
        "status" : "UP",
        "service" : "scheduler"
    }