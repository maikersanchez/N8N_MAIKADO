from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import os
import json
from typing import List, Dict, Any

# Initialize FastAPI app
app = FastAPI()

# Configure Google Generative AI (ensure GOOGLE_API_KEY is set in environment)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('models/gemini-2.5-pro') # Using gemini-2.5-pro for text generation

class LandingPageCopy(BaseModel):
    headline: str
    subheadline: str
    features_benefits: List[Dict[str, str]]
    call_to_action: str
    social_proof: str
    faq: List[Dict[str, str]]
    founder_note: str

class ContentData(BaseModel):
    landing_page_copy: LandingPageCopy
    images: List[Dict[str, str]] # Output from Image Generator Agent
    videos: List[Dict[str, str]] = [] # Output from Video Generator Agent (if implemented)

class ArchitectInput(BaseModel):
    product_name: str
    niche: str
    content_data: ContentData
    language: str = "es" # Default language

@app.post("/")
async def generate_page_structure(input_data: ArchitectInput):
    # --- Prompt Engineering for Page Structure ---
    # This prompt guides the LLM to create a JSON structure based on the A/B fold principles.
    # It needs to be very specific about the desired JSON format.
    prompt = f"""
    Eres un arquitecto de landing pages experto, especializado en diseñar estructuras de páginas de alta conversión para Shopify.
    Tu objetivo es definir la estructura de una landing page como un objeto JSON, basándote en el contenido proporcionado y siguiendo estrictamente los principios de "Above the Fold" y "Below the Fold" para maximizar la conversión.

    Información del Producto:
    Nombre: {input_data.product_name}
    Nicho: {input_data.niche}
    Idioma: {input_data.language}

    Contenido disponible:
    Texto (Copywriter Agent): {json.dumps(input_data.content_data.landing_page_copy.dict(), indent=2)}
    Imágenes (Image Generator Agent): {json.dumps(input_data.content_data.images, indent=2)}
    Videos (Video Generator Agent): {json.dumps(input_data.content_data.videos, indent=2)}

    Principios de Estructura (Above the Fold / Below the Fold):
    Above the Fold:
    1/ Explicar el valor (título)
    2/ Explicar cómo se crea (subtítulo)
    3/ Visualizar (visual principal, galería de imágenes)
    4/ Hacerlo creíble (prueba social)
    5/ Facilitar el siguiente paso (CTA principal)

    Below the Fold:
    6/ Concretar el valor (características y objeciones)
    7/ Inspirar acción (más prueba social)
    8/ Resolver dudas (FAQ)
    9/ Repetir CTA (segundo CTA)
    10/ Hacerse memorable (nota del fundador)

    Genera la estructura de la página en formato JSON. Cada sección debe tener un 'type' (ej. "hero", "features", "cta", "social_proof", "faq") y un 'content' que haga referencia a los datos proporcionados o sea un placeholder para el contenido final.
    Asegúrate de que el JSON sea válido y que cada sección esté claramente definida.

    Formato de salida (JSON):
    ```json
    {{
        "page_structure": [
            {{
                "section_id": "hero",
                "type": "hero",
                "elements": [
                    {{"type": "title", "content_ref": "landing_page_copy.headline"}},
                    {{"type": "subtitle", "content_ref": "landing_page_copy.subheadline"}},
                    {{"type": "main_visual", "content_ref": "images[0].url"}},
                    {{"type": "cta_button", "content_ref": "landing_page_copy.call_to_action"}}
                ]
            }},
            {{
                "section_id": "features",
                "type": "features",
                "elements": [
                    {{"type": "heading", "content": "Características Clave"}},
                    {{"type": "feature_list", "content_ref": "landing_page_copy.features_benefits"}}
                ]
            }},
            // ... more sections following the A/B fold principles ...
            {{
                "section_id": "final_cta",
                "type": "cta",
                "elements": [
                    {{"type": "cta_button", "content_ref": "landing_page_copy.call_to_action"}}
                ]
            }}
        ]
    }}
    ```
    """

    try:
        response = model.generate_content(prompt)
        generated_structure = response.text.strip()
        try:
            parsed_json = json.loads(generated_structure)
            return parsed_json
        except json.JSONDecodeError:
            return {{"error": "Failed to parse LLM response as JSON", "raw_response": generated_structure}}

    except Exception as e:
        return {{"error": f"Error calling Gemini API: {e}"}}

