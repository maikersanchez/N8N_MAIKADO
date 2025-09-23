from fastapi import FastAPI, HTTPException
from typing import Dict, List, Any
import uuid
import datetime
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NocoDB configuration
NOCODB_API_URL = os.getenv("NOCODB_API_URL")
NOCODB_API_TOKEN = os.getenv("NOCODB_API_TOKEN")
NOCODB_TABLE_NAME = os.getenv("NOCODB_TABLE_NAME")

def get_nocodb_headers():
    return {"xc-token": NOCODB_API_TOKEN}

# In-memory storage for analytics events (placeholder for database)
analytics_db: List[Dict] = []

class AnalyticsEvent(BaseModel):
    job_id: str
    event_type: str
    session_id: str
    metadata: Dict[str, Any] = {}

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
        "input_parameters": payload,  # Store payload as a dict
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{NOCODB_API_URL}/api/v2/tables/{NOCODB_TABLE_NAME}/records",
                headers=get_nocodb_headers(),
                json=job_record
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"Error creating job in NocoDB: {e.response.text}")
            raise HTTPException(status_code=500, detail="Failed to create job in database")

    print(f"Job created: {job_id} with payload: {payload}")
    return {"message": "Job creation request received and recorded", "job_id": job_id, "status": "pending"}

@app.post("/jobs/{job_id}/status")
async def update_job_status(job_id: str, new_status: str, shopify_url: str = None, gdrive_url: str = None, error_msg: str = None):
    update_data = {
        "status": new_status,
    }
    if shopify_url:
        update_data["output_shopify_url"] = shopify_url
    if gdrive_url:
        update_data["output_gdrive_url"] = gdrive_url
    if error_msg:
        update_data["error_message"] = error_msg

    async with httpx.AsyncClient() as client:
        try:
            # First, find the record ID based on job_id
            find_response = await client.get(
                f"{NOCODB_API_URL}/api/v2/tables/{NOCODB_TABLE_NAME}/records?where=(job_id,eq,{job_id})",
                headers=get_nocodb_headers()
            )
            find_response.raise_for_status()
            records = find_response.json().get("list", [])
            if not records:
                raise HTTPException(status_code=404, detail="Job not found")
            
            record_id = records[0]["Id"]

            # Now, update the record
            response = await client.patch(
                f"{NOCODB_API_URL}/api/v2/tables/{NOCODB_TABLE_NAME}/records",
                headers=get_nocodb_headers(),
                json={"Id": record_id, **update_data}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"Error updating job in NocoDB: {e.response.text}")
            raise HTTPException(status_code=500, detail="Failed to update job status in database")

    print(f"Job {job_id} status updated to: {new_status}")
    return {"message": "Job status updated successfully", "job_id": job_id, "status": new_status}

@app.get("/jobs/{job_id}")
async def get_job_details(job_id: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{NOCODB_API_URL}/api/v2/tables/{NOCODB_TABLE_NAME}/records?where=(job_id,eq,{job_id})",
                headers=get_nocodb_headers()
            )
            response.raise_for_status()
            records = response.json().get("list", [])
            if not records:
                raise HTTPException(status_code=404, detail="Job not found")
            return records[0]
        except httpx.HTTPStatusError as e:
            print(f"Error getting job from NocoDB: {e.response.text}")
            raise HTTPException(status_code=500, detail="Failed to retrieve job from database")

@app.get("/jobs")
async def get_all_jobs():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{NOCODB_API_URL}/api/v2/tables/{NOCODB_TABLE_NAME}/records",
                headers=get_nocodb_headers()
            )
            response.raise_for_status()
            return response.json().get("list", [])
        except httpx.HTTPStatusError as e:
            print(f"Error getting all jobs from NocoDB: {e.response.text}")
            raise HTTPException(status_code=500, detail="Failed to retrieve jobs from database")

# Analytics endpoints remain the same, using in-memory analytics_db

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
    original_job = await get_job_details(job_id)
    
    # The payload in NocoDB might be a string, so we might need to evaluate it
    import json
    try:
        # Assuming input_parameters is stored as a JSON string
        payload = json.loads(original_job.get("input_parameters", "{}"))
    except (json.JSONDecodeError, TypeError):
        # Fallback if it's not a valid JSON string
        payload = {}

    return await create_job(payload)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
