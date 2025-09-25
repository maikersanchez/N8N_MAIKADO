import json
import asyncio
from playwright.async_api import async_playwright
import google.generativeai as genai
import os

# Configure the generative model (ensure GOOGLE_API_KEY is set)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

async def extract_product_info(url: str) -> str:
    """
    Fetches a product page using a headless browser, then uses a generative AI
    to analyze the HTML and extract key product information in a JSON format.

    Args:
        url (str): The URL of the product page to scrape.

    Returns:
        str: A JSON string containing the extracted product data or an error message.
    """
    print(f"Starting AI-powered extraction for URL: {url}")
    try:
        # Launch Playwright to get the page's full HTML
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                # Give a little extra time for dynamic content to pop in
                await page.wait_for_timeout(3000)
                body_html = await page.locator('body').inner_html()
            except Exception as e:
                print(f"Playwright failed to navigate or get HTML: {e}")
                await browser.close()
                raise
            await browser.close()

        print("HTML content fetched successfully. Sending to AI for analysis...")

        # Dynamically create a model instance within the async function
        model = genai.GenerativeModel('gemini-2.5-pro')

        # The prompt for the AI model
        prompt = f"""
        You are an expert data extractor. Analyze the following HTML code from a product page and extract the key information.

        HTML Content:
        ```html
        {body_html}
        ```

        Based on the HTML, extract the following fields:
        1.  `product_name`: The main, full name of the product.
        2.  `raw_description`: A detailed, comprehensive description of the product.
        3.  `price`: The price or price range. If it's a tiered price, return a list of objects, each with "quantity" and "price". If it's a single price, return a string.
        4.  `image_urls`: A list of all main product image URLs found in the HTML. Ensure URLs are absolute.
        5.  `specifications`: A dictionary of key-value pairs representing the product's technical specifications.

        Return ONLY a valid JSON object with the extracted data. If a field cannot be found, its value should be null or an empty list/object. Do not include any explanatory text or markdown formatting in your response.
        """

        response = await model.generate_content_async(prompt)
        
        print("AI analysis complete. Parsing response.")
        
        # Clean the response to get only the JSON part
        json_str = response.text.strip().replace('```json', '').replace('```', '')
        
        # Validate and return the JSON
        parsed_json = json.loads(json_str)
        return json.dumps(parsed_json, indent=2)

    except Exception as e:
        print(f"An error occurred during the AI extraction process: {e}")
        return json.dumps({"error": f"An error occurred during the AI extraction process: {str(e)}"}, indent=2)