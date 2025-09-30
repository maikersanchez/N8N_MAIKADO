from fastapi import FastAPI
from pydantic import BaseModel
import os
from typing import List, Optional
from minio import Minio
from minio.error import S3Error
import io
import datetime
from urllib.parse import urlparse
import httpx
import json
import asyncio
import random
from huggingface_hub import InferenceClient
from PIL import Image
from moviepy.editor import VideoFileClip, concatenate_videoclips
import google.generativeai as genai

# Initialize FastAPI app
app = FastAPI()

# --- Clients and Configurations ---
# ComfyUI
COMFYUI_MODAL_ENDPOINT = os.environ.get("COMFYUI_MODAL_ENDPOINT")

# MinIO
MINIO_ENDPOINT_URL = os.environ.get("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET")
MINIO_USE_SSL = os.environ.get("MINIO_USE_SSL", "true").lower() == "true"

minio_client = None
if MINIO_ENDPOINT_URL:
    parsed_url = urlparse(MINIO_ENDPOINT_URL)
    minio_endpoint = parsed_url.netloc or parsed_url.path
    minio_client = Minio(minio_endpoint, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=MINIO_USE_SSL)

# Hugging Face
hf_client = InferenceClient(provider="auto", token=os.environ.get("HF_TOKEN"))

# Google Generative AI for translation
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
translation_model = genai.GenerativeModel('gemini-pro')


# --- Pydantic Models ---
class ProductData(BaseModel):
    product_name: str
    raw_description: str
    image_urls: Optional[List[str]] = []

class UGCScene(BaseModel):
    scene: int
    time: str
    visuals: str
    dialogue: str

class UGCVideoScript(BaseModel):
    title: str
    ugc_video_script: List[UGCScene]

class VideoGeneratorInput(BaseModel):
    product_data: ProductData
    script_data: UGCVideoScript
    video_count: int = 1
    seed: Optional[int] = None

class GeneratedVideo(BaseModel):
    url: str = None
    description: str = None


# --- Helper Functions ---
async def translate_to_english(text: str) -> str:
    try:
        response = await translation_model.generate_content_async(f"Translate the following text to English: {text}")
        return response.text.strip()
    except Exception as e:
        print(f"Error during translation: {e}")
        return text # Fallback to original text

async def generate_image_for_scene(scene: UGCScene, reference_image_bytes: Optional[bytes]) -> bytes:
    english_visuals = await translate_to_english(scene.visuals)
    english_dialogue = await translate_to_english(scene.dialogue)
    prompt = f"Scene: {english_visuals}. Dialogue: {english_dialogue}"

    if reference_image_bytes:
        image: Image.Image = hf_client.image_to_image(
            image=reference_image_bytes,
            prompt=prompt,
            model="stabilityai/stable-diffusion-xl-refiner-1.0",
        )
    else:
        image: Image.Image = hf_client.text_to_image(
            prompt,
            model="stabilityai/stable-diffusion-xl-base-1.0",
        )
    
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

async def generate_video_fragment(image_bytes: bytes, prompt: str, seed: Optional[int] = None) -> bytes:
    # Load workflow
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workflow_path = os.path.join(script_dir, "comfyui_api_wan2_2_5B_t2v.json")
    with open(workflow_path, "r") as f:
        workflow = json.load(f)

    # Upload image to ComfyUI
    async with httpx.AsyncClient(timeout=None) as client:
        files = {'image': ('scene_image.png', image_bytes)}
        upload_response = await client.post(f"{COMFYUI_MODAL_ENDPOINT}/upload/image", files=files)
        upload_response.raise_for_status()
        image_filename = upload_response.json().get("name")

    # Modify workflow
    workflow["prompt"]["6"]["inputs"]["text"] = prompt
    workflow["prompt"]["56"]["inputs"]["image"] = image_filename
    if seed is not None:
        workflow["prompt"]["3"]["inputs"]["seed"] = seed
    else:
        workflow["prompt"]["3"]["inputs"]["seed"] = random.randint(0, 0xFFFFFFFF)


    # Start job and poll for completion
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(f"{COMFYUI_MODAL_ENDPOINT}/prompt", json=workflow)
        response.raise_for_status()
        prompt_id = response.json().get("prompt_id")

        for _ in range(60):
            await asyncio.sleep(7)
            history_response = await client.get(f"{COMFYUI_MODAL_ENDPOINT}/history/{prompt_id}")
            history_data = history_response.json()
            if history_data and prompt_id in history_data and history_data[prompt_id].get("status", {}).get("completed"):
                outputs = history_data[prompt_id].get("outputs", {})
                all_videos = [vid for node in outputs.values() for vid in node.get("videos", [])]
                output_video = next((vid for vid in all_videos if vid.get("type") == "output"), None)
                if output_video:
                    video_filename = output_video.get("filename")
                    subfolder = output_video.get("subfolder")
                    params = {"filename": video_filename}
                    if subfolder:
                        params["subfolder"] = subfolder
                    video_response = await client.get(f"{COMFYUI_MODAL_ENDPOINT}/view", params=params)
                    video_response.raise_for_status()
                    return video_response.content
                else:
                    raise Exception("Video filename not found in history.")
    raise Exception("Job timed out or failed.")


# --- Main Endpoint ---
@app.post("/")
async def generate_videos(input_data: VideoGeneratorInput):
    generated_videos_list: List[GeneratedVideo] = []

    # Get reference image
    reference_image_bytes = None
    if input_data.product_data.image_urls:
        try:
            async with httpx.AsyncClient() as client_http:
                response = await client_http.get(input_data.product_data.image_urls[0])
                response.raise_for_status()
                reference_image_bytes = response.content
        except Exception as e:
            print(f"Error fetching reference image: {e}")

    for i in range(input_data.video_count):
        video_fragments = []
        try:
            for scene in input_data.script_data.ugc_video_script:
                # 1. Generate image for scene
                scene_image_bytes = await generate_image_for_scene(scene, reference_image_bytes)
                
                # 2. Generate video fragment for scene
                english_prompt = await translate_to_english(f"Scene: {scene.visuals}. Dialogue: {scene.dialogue}")
                video_fragment_bytes = await generate_video_fragment(scene_image_bytes, english_prompt, input_data.seed)
                
                # Save fragment to a temporary file
                with open(f"fragment_{i}_{scene.scene}.mp4", "wb") as f:
                    f.write(video_fragment_bytes)
                video_fragments.append(f"fragment_{i}_{scene.scene}.mp4")

            # 3. Combine video fragments
            clips = [VideoFileClip(f) for f in video_fragments]
            final_clip = concatenate_videoclips(clips)
            final_video_path = f"final_video_{i}.mp4"
            final_clip.write_videofile(final_video_path, codec="libx264")

            # 4. Upload to MinIO
            if minio_client:
                with open(final_video_path, "rb") as f:
                    video_data = f.read()
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                video_filename_minio = f"video_{i+1}_{timestamp}.mp4"
                video_object_name = f"{input_data.script_data.title}/{video_filename_minio}"
                
                minio_client.put_object(
                    MINIO_BUCKET,
                    video_object_name,
                    io.BytesIO(video_data),
                    len(video_data),
                    content_type='video/mp4'
                )
                
                base_url = MINIO_ENDPOINT_URL
                if not base_url.startswith("http"):
                    base_url = f"http{'s' if MINIO_USE_SSL else ''}://{base_url}"
                video_url = f"{base_url}/{MINIO_BUCKET}/{video_object_name}"
                
                generated_videos_list.append(GeneratedVideo(
                    url=video_url,
                    description=f"Generated video {i+1} for {input_data.script_data.title}"
                ))

            # Clean up temporary files
            for f in video_fragments:
                os.remove(f)
            os.remove(final_video_path)

        except Exception as e:
            print(f"An unexpected error occurred during video generation: {e}")
            generated_videos_list.append(GeneratedVideo(
                url=f"http://placeholder.com/error_generation.mp4",
                description=f"Failed to generate video {i+1} for {input_data.script_data.title}"
            ))

    return generated_videos_list
