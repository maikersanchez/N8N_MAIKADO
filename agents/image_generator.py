from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import os
import base64
from typing import List
from minio import Minio
from minio.error import S3Error
import io
import datetime

# Initialize FastAPI app
app = FastAPI()

# Configure Google Generative AI
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-pro-vision') # Placeholder for image generation model

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

class ProductData(BaseModel):
    product_name: str
    raw_description: str

class ImageGeneratorInput(BaseModel):
    product_data: ProductData
    image_count: int = 1

class GeneratedImage(BaseModel):
    url: str = None
    description: str = None

@app.post("/")
async def generate_images(input_data: ImageGeneratorInput):
    prompt_text = f"""
    Generate {input_data.image_count} professional, high-quality product images for:
    Product Name: {input_data.product_data.product_name}
    Description: {input_data.product_data.raw_description}

    Focus on creating images that highlight benefits and appeal to customers.
    Consider different angles, contexts (e.g., lifestyle, close-up of features).
    """

    try:
        # This is a simplified representation.
        response = model.generate_content(prompt_text)

        generated_images_list: List[GeneratedImage] = []
        
        # Assuming response.parts contains image data
        # This is a placeholder and needs to be adapted to the actual model response
        if hasattr(response, 'parts'):
            for i, part in enumerate(response.parts):
                if part.mime_type.startswith("image/"):
                    image_data = part.data
                    
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
                            io.BytesIO(image_data),
                            len(image_data),
                            content_type='image/png'
                        )
                        
                        # Construct the public URL
                        image_url = f"http{'s' if MINIO_USE_SSL else ''}://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{object_name}"
                        
                        generated_images_list.append(GeneratedImage(
                            url=image_url,
                            description=f"Generated image {i+1} for {input_data.product_data.product_name}"
                        ))
                    except S3Error as exc:
                        print(f"Error uploading to MinIO: {exc}")
                        # Fallback to placeholder if upload fails
                        generated_images_list.append(GeneratedImage(
                            url=f"http://placeholder.com/error_upload.jpg",
                            description=f"Failed to upload image {i+1} for {input_data.product_data.product_name}"
                        ))
        
        if not generated_images_list:
             # Placeholder if no images are generated from the model
            for i in range(input_data.image_count):
                generated_images_list.append(GeneratedImage(
                    url=f"http://placeholder.com/image_{i+1}.jpg",
                    description=f"Generated image {i+1} for {input_data.product_data.product_name}"
                ))

        return generated_images_list

    except Exception as e:
        return {"error": f"Error calling Google Image API: {e}"}
