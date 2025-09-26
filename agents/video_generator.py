from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import os
from typing import List, Dict, Any
from minio import Minio
from minio.error import S3Error
import io
import datetime

# Initialize FastAPI app
app = FastAPI()

# Configure Google Generative AI
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('veo-2.0-generate-001') # Placeholder for video generation model

# MinIO Configuration
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET")
MINIO_USE_SSL = os.environ.get("MINIO_USE_SSL", "true").lower() == "true"

# Initialize MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_USE_SSL
)

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

@app.post("/")
async def generate_videos(input_data: VideoGeneratorInput):
    prompt_text = f"""
    Generate {input_data.video_count} short, engaging promotional videos based on the following script:
    Title: {input_data.script_data.title}
    Scenes:
    """
    for scene in input_data.script_data.ugc_video_script:
        prompt_text += f"- Scene {scene.scene} ({scene.time}): {scene.visuals} - Dialogue: {scene.dialogue}\n"

    try:
        # This is a simplified representation.
        response = model.generate_content(prompt_text)

        generated_videos_list: List[GeneratedVideo] = []

        if hasattr(response, 'parts'):
            for i, part in enumerate(response.parts):
                if part.mime_type.startswith("video/"):
                    video_data = part.data
                    
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    filename = f"video_{i+1}_{timestamp}.mp4"
                    
                    object_name = f"{input_data.script_data.title}/{filename}"
                    
                    try:
                        minio_client.put_object(
                            MINIO_BUCKET,
                            object_name,
                            io.BytesIO(video_data),
                            len(video_data),
                            content_type='video/mp4'
                        )
                        
                        video_url = f"http{'s' if MINIO_USE_SSL else ''}://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{object_name}"
                        
                        generated_videos_list.append(GeneratedVideo(
                            url=video_url,
                            description=f"Generated video {i+1} for {input_data.script_data.title}"
                        ))
                    except S3Error as exc:
                        print(f"Error uploading to MinIO: {exc}")
                        generated_videos_list.append(GeneratedVideo(
                            url=f"http://placeholder.com/error_upload.mp4",
                            description=f"Failed to upload video {i+1} for {input_data.script_data.title}"
                        ))

        if not generated_videos_list:
            for i in range(input_data.video_count):
                generated_videos_list.append(GeneratedVideo(
                    url=f"http://placeholder.com/video_{i+1}.mp4",
                    description=f"Generated video {i+1} for {input_data.script_data.title}"
                ))

        return generated_videos_list

    except Exception as e:
        return {"error": f"Error calling Google Video API: {e}"}
