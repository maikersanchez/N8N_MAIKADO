from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import os
import json

# Initialize FastAPI app
app = FastAPI()

# Configure Google Generative AI (ensure GOOGLE_API_KEY is set in environment)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('models/gemini-1.5-pro-latest') # Using gemini-pro for text generation

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
    # --- Prompt Engineering for UGC Video Script ---
    prompt = f"""
    Eres un copywriter experto en marketing digital, especializado en la creación de guiones para videos de contenido generado por el usuario (UGC) de alta conversión.
    Tu objetivo es generar un guion de video persuasivo que siga una estructura clara para un anuncio de video corto.

    Información del Producto:
    Nombre: {input_data.product_data.product_name}
    Descripción: {input_data.product_data.raw_description}

    Dolores del Cliente (identificados o sugeridos): {input_data.customer_pains}

    Idioma de salida: {input_data.language}
    Moneda de destino: {input_data.currency}

    Genera el siguiente guion para un video UGC:

    **Estructura del Guion:**
    1.  **Hook (Gancho):** Una primera escena impactante que capte la atención en los primeros 3 segundos.
    2.  **Problem (Problema):** Muestra el problema que el producto resuelve, conectando con los dolores del cliente.
    3.  **Solution (Solución):** Presenta el producto como la solución definitiva.
    4.  **Call to Action (Llamado a la Acción):** Un llamado a la acción claro y convincente, mencionando el precio en la moneda de destino si es posible.

    **Formato de Salida (JSON con Storyboard):**
    ```json
    {{
        "title": "Guion de Video UGC para {input_data.product_data.product_name}",
        "ugc_video_script": [
            {{
                "scene": 1,
                "time": "0-3s",
                "visuals": "Descripción visual de la escena (ej. 'Primer plano de una persona frustrada con [problema]').",
                "dialogue": "Línea de diálogo o texto en pantalla."
            }},
            {{
                "scene": 2,
                "time": "3-8s",
                "visuals": "Descripción visual de la escena (ej. 'Mostrando el [problema] en acción').",
                "dialogue": "Línea de diálogo o texto en pantalla."
            }},
            {{
                "scene": 3,
                "time": "8-12s",
                "visuals": "Descripción visual de la escena (ej. 'El producto [nombre del producto] entra en escena y se muestra cómo funciona').",
                "dialogue": "Línea de diálogo o texto en pantalla."
            }},
            {{
                "scene": 4,
                "time": "12-15s",
                "visuals": "Descripción visual de la escena (ej. 'Persona sonriendo y usando el producto con satisfacción. Logo y URL del sitio web en pantalla').",
                "dialogue": "Línea de diálogo o texto en pantalla con el Call to Action."
            }}
        ]
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
            return {"error": "Failed to parse LLM response as JSON", "raw_response": generated_content}

    except Exception as e:
        return {"error": f"Error calling Gemini API: {e}"}

