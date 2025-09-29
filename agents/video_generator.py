from fastapi import FastAPI
from pydantic import BaseModel
import os
from typing import List
from minio import Minio
from minio.error import S3Error
import io
import datetime
from urllib.parse import urlparse
import httpx
import json

# Initialize FastAPI app
app = FastAPI()

# --- ComfyUI Modal Endpoint ---
COMFYUI_MODAL_ENDPOINT = os.environ.get("COMFYUI_MODAL_ENDPOINT")

# --- MinIO Configuration ---
MINIO_ENDPOINT_URL = os.environ.get("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET")
MINIO_USE_SSL = os.environ.get("MINIO_USE_SSL", "true").lower() == "true"

minio_client = None
if MINIO_ENDPOINT_URL:
    parsed_url = urlparse(MINIO_ENDPOINT_URL)
    minio_endpoint = parsed_url.netloc or parsed_url.path
    # Initialize MinIO client
    minio_client = Minio(
        minio_endpoint,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_USE_SSL
    )

# --- Pydantic Models ---
class UGCScene(BaseModel):
    scene: int
    time: str
    visuals: str
    dialogue: str

class UGCVideoScript(BaseModel):
    title: str
    ugc_video_script: List[UGCScene]

class VideoGeneratorInput(BaseModel):
    script_data: UGCVideoScript
    video_count: int = 1

class GeneratedVideo(BaseModel):
    url: str = None
    description: str = None

# --- FastAPI Endpoint ---
@app.post("/")
async def generate_videos(input_data: VideoGeneratorInput):
    if not COMFYUI_MODAL_ENDPOINT:
        return {"error": "COMFYUI_MODAL_ENDPOINT environment variable is not set."}

    # Load the ComfyUI workflow from a file
    try:
        with open("agents/comfyui_api_wan2_2_5B_t2v.json", "r") as f:
            workflow = json.load(f)
    except FileNotFoundError:
        return {"error": "comfyui_api_wan2_2_5B_t2v.json not found. Please provide the workflow file in the agents directory."}

    # Construct the prompt from all scenes
    prompt_parts = []
    for scene in input_data.script_data.ugc_video_script:
        prompt_parts.append(f"Scene {scene.scene}: {scene.visuals}. Dialogue: {scene.dialogue}")
    full_prompt = " ".join(prompt_parts)

    # Modify the workflow with the new prompt
    workflow["6"]["inputs"]["text"] = full_prompt

    generated_videos_list: List[GeneratedVideo] = []

    for i in range(input_data.video_count):
        try:
            # Store the request JSON in MinIO
            if minio_client:
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                request_filename = f"request_{i+1}_{timestamp}.json"
                request_object_name = f"{input_data.script_data.title}/{request_filename}"
                request_data = json.dumps(workflow, indent=2).encode('utf-8')
                
                try:
                    minio_client.put_object(
                        MINIO_BUCKET,
                        request_object_name,
                        io.BytesIO(request_data),
                        len(request_data),
                        content_type='application/json'
                    )
                except S3Error as exc:
                    print(f"Error uploading request to MinIO: {exc}")

            # Call the ComfyUI Modal endpoint
            async with httpx.AsyncClient(timeout=None) as client:
                response = await client.post(COMFYUI_MODAL_ENDPOINT, json=workflow)
                response.raise_for_status()
                video_data = response.content

            if minio_client:
                # Create a unique filename for the video
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                video_filename = f"video_{i+1}_{timestamp}.mp4"
                
                # Define the object name in MinIO
                video_object_name = f"{input_data.script_data.title}/{video_filename}"
                
                # Upload the video to MinIO
                try:
                    minio_client.put_object(
                        MINIO_BUCKET,
                        video_object_name,
                        io.BytesIO(video_data),
                        len(video_data),
                        content_type='video/mp4'
                    )
                    
                    # Construct the public URL
                    video_url = f"http{'s' if MINIO_USE_SSL else ''}://{MINIO_ENDPOINT_URL}/{MINIO_BUCKET}/{video_object_name}"
                    
                    generated_videos_list.append(GeneratedVideo(
                        url=video_url,
                        description=f"Generated video {i+1} for {input_data.script_data.title}"
                    ))
                except S3Error as exc:
                    print(f"Error uploading video to MinIO: {exc}")
                    generated_videos_list.append(GeneratedVideo(
                        url=f"http://placeholder.com/error_upload.mp4",
                        description=f"Failed to upload video {i+1} for {input_data.script_data.title}"
                    ))
            else:
                # Fallback if MinIO is not configured
                generated_videos_list.append(GeneratedVideo(
                    url=f"http://placeholder.com/video_{i+1}.mp4",
                    description=f"Generated video {i+1} for {input_data.script_data.title} (MinIO not configured)"
                ))

        except httpx.HTTPStatusError as e:
            print(f"Error calling ComfyUI endpoint: {e}")
            generated_videos_list.append(GeneratedVideo(
                url=f"http://placeholder.com/error_generation.mp4",
                description=f"Failed to generate video {i+1} for {input_data.script_data.title}"
            ))
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            generated_videos_list.append(GeneratedVideo(
                url=f"http://placeholder.com/error_generation.mp4",
                description=f"Failed to generate video {i+1} for {input_data.script_data.title}"
            ))

    return generated_videos_list
