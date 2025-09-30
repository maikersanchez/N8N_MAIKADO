from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import os
import json

# Initialize FastAPI app
app = FastAPI()

# Configure Google Generative AI (ensure GOOGLE_API_KEY is set in environment)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-pro') # Using gemini-pro for text generation

class ProductData(BaseModel):
    product_name: str
    raw_description: str
    # Add other fields as needed from extractor agent output

class CopywriterInput(BaseModel):
    product_data: ProductData
    customer_pains: str # Comma-separated string of customer pains
    language: str = "es" # Default language
    currency: str = "USD" # Default currency

@app.post("/")
async def generate_copy(input_data: CopywriterInput):
    # --- Prompt Engineering for UGC Video Script and Landing Page Copy ---
    prompt = f"""
    Eres un copywriter experto en marketing digital, especializado en la creación de contenido de alta conversión.
    Tu objetivo es generar tanto un guion de video persuasivo como el texto completo para una landing page.

    Información del Producto:
    Nombre: {input_data.product_data.product_name}
    Descripción: {input_data.product_data.raw_description}

    Dolores del Cliente (identificados o sugeridos): {input_data.customer_pains}

    Idioma de salida: {input_data.language}
    Moneda de destino: {input_data.currency}

    Genera el siguiente contenido en formato JSON:

    1.  **Guion de Video UGC:** Un guion de video que siga la estructura de Hook, Problema, Solución y Llamado a la Acción.
    2.  **Texto para Landing Page:** Todo el texto necesario para una landing page de alta conversión, incluyendo headline, subheadline, beneficios, llamado a la acción, etc.

    **Formato de Salida (JSON):**
    ```json
    {{
        "ugc_video_script": {{
            "title": "Guion de Video UGC para {input_data.product_data.product_name}",
            "scenes": [
                {{
                    "scene": 1,
                    "time": "0-3s",
                    "visuals": "Descripción visual de la escena.",
                    "dialogue": "Línea de diálogo o texto en pantalla."
                }},
                {{
                    "scene": 2,
                    "time": "3-8s",
                    "visuals": "Descripción visual de la escena.",
                    "dialogue": "Línea de diálogo o texto en pantalla."
                }},
                {{
                    "scene": 3,
                    "time": "8-12s",
                    "visuals": "Descripción visual de la escena.",
                    "dialogue": "Línea de diálogo o texto en pantalla."
                }},
                {{
                    "scene": 4,
                    "time": "12-15s",
                    "visuals": "Descripción visual de la escena.",
                    "dialogue": "Línea de diálogo o texto en pantalla con el Call to Action."
                }}
            ]
        }},
        "landing_page_copy": {{
            "headline": "El titular principal de la página.",
            "subheadline": "Un subtitulo que complemente al titular.",
            "features_benefits": [
                {{
                    "feature": "Característica 1",
                    "benefit": "Beneficio de la característica 1."
                }},
                {{
                    "feature": "Característica 2",
                    "benefit": "Beneficio de la característica 2."
                }}
            ],
            "call_to_action": "El texto para el botón de llamado a la acción principal.",
            "social_proof": "Un testimonio o prueba social.",
            "faq": [
                {{
                    "question": "Pregunta frecuente 1",
                    "answer": "Respuesta a la pregunta 1."
                }},
                {{
                    "question": "Pregunta frecuente 2",
                    "answer": "Respuesta a la pregunta 2."
                }}
            ],
            "founder_note": "Una nota del fundador para conectar con los clientes."
        }}
    }}
    ```
    """

    try:
        response = model.generate_content(prompt)
        # Assuming the model returns a JSON string directly
        generated_content = response.text.strip()
        # Attempt to parse the JSON. If it fails, return raw text or error.
        try:
            # Clean the response to extract only the JSON part
            json_str = generated_content.split('```json')[1].split('```')[0].strip()
            parsed_json = json.loads(json_str)
            return parsed_json
        except (json.JSONDecodeError, IndexError):
            return {{"error": "Failed to parse LLM response as JSON", "raw_response": generated_content}}

    except Exception as e:
        return {{"error": f"Error calling Gemini API: {e}"}}
