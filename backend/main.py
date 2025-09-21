from fastapi import FastAPI, HTTPException
from typing import Dict, List, Any
import uuid
import datetime # Import datetime for timestamps
from pydantic import BaseModel # Import BaseModel for AnalyticsEvent
from starlette.middleware.cors import CORSMiddleware # Import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow requests from your Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# In-memory storage for jobs (placeholder for database)
jobs_db: Dict[str, Dict] = {}
# In-memory storage for analytics events (placeholder for database)
analytics_db: List[Dict] = [] # Using a list to simulate a collection of events

class AnalyticsEvent(BaseModel):
    job_id: str
    event_type: str # e.g., 'page_view', 'add_to_cart', 'purchase'
    session_id: str
    metadata: Dict[str, Any] = {} # Flexible metadata

@app.get("/")
async def read_root():
    return {"message": "Welcome to WF Makiado Backend API!"}

@app.post("/create-job")
async def create_job(payload: dict):
    job_id = str(uuid.uuid4())
    current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    job_record = {
        "job_id": job_id,
        "status": "pending",
        "input_parameters": payload,
        "output_shopify_url": None,
        "output_gdrive_url": None,
        "error_message": None,
        "created_at": current_time,
        "updated_at": current_time
    }
    jobs_db[job_id] = job_record
    print(f"Job created: {job_id} with payload: {payload}")
    return {"message": "Job creation request received and recorded", "job_id": job_id, "status": "pending"}

@app.post("/jobs/{job_id}/status")
async def update_job_status(job_id: str, new_status: str, shopify_url: str = None, gdrive_url: str = None, error_msg: str = None):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs_db[job_id]
    job["status"] = new_status
    job["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if shopify_url:
        job["output_shopify_url"] = shopify_url
    if gdrive_url:
        job["output_gdrive_url"] = gdrive_url
    if error_msg:
        job["error_message"] = error_msg

    print(f"Job {job_id} status updated to: {new_status}")
    return {"message": "Job status updated successfully", "job_id": job_id, "status": new_status}

@app.get("/jobs/{job_id}")
async def get_job_details(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs_db[job_id]

@app.get("/jobs")
async def get_all_jobs():
    return list(jobs_db.values())

@app.post("/analytics/ingest")
async def ingest_analytics_event(event: AnalyticsEvent):
    event_record = event.dict()
    event_record["event_id"] = str(uuid.uuid4())
    event_record["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    analytics_db.append(event_record)
    print(f"Analytics event ingested: {event.event_type} for job {event.job_id}")
    return {"message": "Analytics event ingested successfully", "event_id": event_record["event_id"]}

@app.get("/analytics/events")
async def get_all_analytics_events():
    return analytics_db

@app.get("/analytics/summary")
async def get_analytics_summary():
    summary = {}
    for event in analytics_db:
        job_id = event["job_id"]
        event_type = event["event_type"]
        
        if job_id not in summary:
            summary[job_id] = {
                "total_views": 0,
                "total_purchases": 0,
                "total_revenue": 0.0,
                "conversion_rate": 0.0
            }
        
        if event_type == "page_view":
            summary[job_id]["total_views"] += 1
        elif event_type == "purchase":
            summary[job_id]["total_purchases"] += 1
            revenue = event["metadata"].get("value", 0.0)
            summary[job_id]["total_revenue"] += float(revenue)
            
    for job_id, data in summary.items():
        if data["total_views"] > 0:
            data["conversion_rate"] = (data["total_purchases"] / data["total_views"]) * 100
        
    return summary

@app.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")

    original_job = jobs_db[job_id]
    new_job_id = str(uuid.uuid4())
    current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

    new_job_record = {
        "job_id": new_job_id,
        "status": "pending",
        "input_parameters": original_job["input_parameters"],
        "output_shopify_url": None,
        "output_gdrive_url": None,
        "error_message": None,
        "created_at": current_time,
        "updated_at": current_time
    }
    jobs_db[new_job_id] = new_job_record
    print(f"Job {job_id} retried as new job {new_job_id}")
    return {"message": "Job retried successfully", "new_job_id": new_job_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)