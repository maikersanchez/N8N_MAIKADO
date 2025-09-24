import json
import asyncio
from playwright.async_api import async_playwright
import google.generativeai as genai
import os

# Configure the generative model (ensure GOOGLE_API_KEY is set)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

async def list_available_gemini_models() -> str:
    """Lists available Gemini models for debugging purposes."""
    try:
        print("Attempting to list available Gemini models...")
        models = genai.list_models()
        available_models = []
        for m in models:
            available_models.append({
                "name": m.name,
                "supported_generation_methods": m.supported_generation_methods
            })
        print(f"Available models: {json.dumps(available_models, indent=2)}")
        return json.dumps({"available_models": available_models}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to list models: {str(e)}"}, indent=2)

async def extract_product_info(url: str) -> str:
    """
    Temporarily modified to list available models for debugging.
    """
    return await list_available_gemini_models()