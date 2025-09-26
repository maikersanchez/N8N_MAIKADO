from fastapi import FastAPI, Body, Response
from typing import Annotated
from minio import Minio
from minio.error import S3Error
import os
from urllib.parse import urlparse

# Import the app object from each agent module
from architect import app as architect_app
from copywriter import app as copywriter_app
from image_generator import app as image_generator_app
from video_generator import app as video_generator_app
from web_developer import app as web_developer_app

# Import the function from the extractor script
from extractor import extract_product_info

# Main FastAPI app that will orchestrate all agents
app = FastAPI(title="Maikado Agents Service")

# --- Extractor Endpoint ---
# Since extractor is a simple function, we create an endpoint for it directly.
@app.post("/extractor/extract")
async def run_extractor(url: Annotated[str, Body(embed=True)]):
    """
    Endpoint to run the product information extractor.
    Accepts a URL and returns the scraped data.
    """
    return await extract_product_info(url)

# --- MinIO Health Check Endpoint ---
@app.get("/health/minio")
async def minio_health_check(response: Response):
    """
    Checks the connection to MinIO and returns the status.
    """
    try:
        # MinIO Configuration
        MINIO_ENDPOINT_URL = os.environ.get("MINIO_ENDPOINT")
        MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY")
        MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY")
        MINIO_USE_SSL = os.environ.get("MINIO_USE_SSL", "true").lower() == "true"

        if not all([MINIO_ENDPOINT_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY]):
            response.status_code = 500
            return {"status": "error", "error": "MinIO environment variables are not set."}

        # Parse the endpoint to remove any path
        parsed_url = urlparse(MINIO_ENDPOINT_URL)
        minio_endpoint = parsed_url.netloc or parsed_url.path # Handles cases with or without scheme

        minio_client = Minio(
            minio_endpoint,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_USE_SSL
        )

        # Check if the client can list buckets
        minio_client.list_buckets()

        return {"status": "ok", "message": "MinIO connection is successful."}
    except S3Error as e:
        response.status_code = 500
        return {"status": "error", "error": f"MinIO S3 Error: {e}"}
    except Exception as e:
        response.status_code = 500
        return {"status": "error", "error": f"An unexpected error occurred: {e}"}


# --- Mount other agents ---
# Mount each agent's FastAPI app as a sub-application
app.mount("/architect", architect_app)
app.mount("/copywriter", copywriter_app)
app.mount("/image_generator", image_generator_app)
app.mount("/video_generator", video_generator_app)
app.mount("/web_developer", web_developer_app)

@app.get("/")
def read_root():
    return {"message": "Maikado Agents Service is running. Access agents at their respective sub-paths."}

# To run this main app for local development:
# uvicorn agents.main:app --reload --port 8001
