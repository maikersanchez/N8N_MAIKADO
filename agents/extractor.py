import requests
from bs4 import BeautifulSoup
import json

def extract_product_info(url):
    """
    Fetches a product page URL, parses its HTML content, and extracts key product information.

    Args:
        url (str): The URL of the product page to scrape.

    Returns:
        str: A JSON string containing the extracted product data or an error message.
    """
    try:
        # Use a common user-agent to avoid simple bot detection
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Product Title ---
        try:
            product_title_element = soup.find('h1') # Find the first h1 tag
            product_name = product_title_element.text.strip() if product_title_element else 'N/A'
        except Exception:
            product_name = 'N/A'

        # --- Product Description ---
        try:
            description_div = soup.find('div', id='product-detail') # This id is a more likely guess
            raw_description = description_div.get_text(separator='\n').strip() if description_div else 'N/A'
        except Exception:
            raw_description = 'N/A'

        # --- Product Price ---
        try:
            # This is a guess. Alibaba's price structure is complex.
            price_element = soup.find(lambda tag: (tag.name == 'span' or tag.name == 'div') and 'price' in ''.join(tag.get('class', [])))
            price = price_element.text.strip() if price_element else 'N/A'
        except Exception:
            price = 'N/A'

        # --- Product Image URLs ---
        try:
            image_urls = []
            # This is a guess. Find a gallery container and get all images within it.
            gallery_container = soup.find('div', class_=lambda x: x and 'gallery' in x)
            if gallery_container:
                image_elements = gallery_container.find_all('img')
                for img in image_elements:
                    if img.get('src'):
                        image_urls.append(img.get('src'))
            # Fallback if the main gallery isn't found
            if not image_urls:
                main_image = soup.find('img', class_=lambda x: x and 'main' in x)
                if main_image and main_image.get('src'):
                    image_urls.append(main_image.get('src'))
        except Exception:
            image_urls = []

        # --- Product Specifications ---
        try:
            specifications = {}
            # This is a guess. Find a container for specs, e.g., a div with id="product-specs"
            specs_container = soup.find('div', id=lambda x: x and 'spec' in x.lower())
            if specs_container:
                # Assuming specs are in a table
                table_rows = specs_container.find_all('tr')
                for row in table_rows:
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        key = cells[0].text.strip()
                        value = cells[1].text.strip()
                        if key and value:
                            specifications[key] = value
        except Exception:
            specifications = {}

        product_data = {
            'product_url': url,
            'product_name': product_name,
            'raw_description': raw_description,
            'price': price,
            'image_urls': image_urls,
            'specifications': specifications,
        }

        return json.dumps(product_data, indent=2)

    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"HTTP Request failed: {e}"}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"An error occurred: {e}"}, indent=2)

