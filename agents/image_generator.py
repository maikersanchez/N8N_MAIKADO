from fastapi import FastAPI
from pydantic import BaseModel
import os
from typing import List
from minio import Minio
from minio.error import S3Error
import io
import datetime
from urllib.parse import urlparse
from huggingface_hub import InferenceClient
from PIL import Image

# Initialize FastAPI app
app = FastAPI()

# --- Hugging Face Inference Client ---
client = InferenceClient(
    provider="auto",
    token=os.environ.get("HF_TOKEN"),
)

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
class ProductData(BaseModel):
    product_name: str
    raw_description: str

class ImageGeneratorInput(BaseModel):
    product_data: ProductData
    image_count: int = 1

class GeneratedImage(BaseModel):
    url: str = None
    description: str = None

# --- FastAPI Endpoint ---
@app.post("/")
async def generate_images(input_data: ImageGeneratorInput):
    prompt_text = f"""
    A professional, high-quality product image of: {input_data.product_data.product_name}.
    {input_data.product_data.raw_description}.
    The image should be suitable for an e-commerce website.
    """

    generated_images_list: List[GeneratedImage] = []

    for i in range(input_data.image_count):
        try:
            # Generate the image
            image: Image.Image = client.text_to_image(
                prompt_text,
                model="stabilityai/stable-diffusion-xl-base-1.0",
            )

            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            if minio_client:
                # Create a unique filename
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"image_{i+1}_{timestamp}.png"
                
                # Define the object name in MinIO
                object_name = f"{input_data.product_data.product_name}/{filename}"
                
                # Upload the image to MinIO
                try:
                    minio_client.put_object(
                        MINIO_BUCKET,
                        object_name,
                        io.BytesIO(img_byte_arr),
                        len(img_byte_arr),
                        content_type='image/png'
                    )
                    
                    # Construct the public URL
                    image_url = f"http{'s' if MINIO_USE_SSL else ''}://{MINIO_ENDPOINT_URL}/{MINIO_BUCKET}/{object_name}"
                    
                    generated_images_list.append(GeneratedImage(
                        url=image_url,
                        description=f"Generated image {i+1} for {input_data.product_data.product_name}"
                    ))
                except S3Error as exc:
                    print(f"Error uploading to MinIO: {exc}")
                    # Fallback to a placeholder if upload fails
                    generated_images_list.append(GeneratedImage(
                        url=f"http://placeholder.com/error_upload.jpg",
                        description=f"Failed to upload image {i+1} for {input_data.product_data.product_name}"
                    ))
            else:
                # Fallback if MinIO is not configured
                generated_images_list.append(GeneratedImage(
                    url=f"http://placeholder.com/image_{i+1}.jpg",
                    description=f"Generated image {i+1} for {input_data.product_data.product_name} (MinIO not configured)"
                ))

        except Exception as e:
            print(f"Error generating image: {e}")
            generated_images_list.append(GeneratedImage(
                url=f"http://placeholder.com/error_generation.jpg",
                description=f"Failed to generate image {i+1} for {input_data.product_data.product_name}"
            ))

    return generated_images_list
