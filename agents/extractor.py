import json
import asyncio
from playwright.async_api import async_playwright

async def extract_product_info(url: str) -> str:
    """
    Fetches a product page URL using a headless browser (Playwright),
    parses its content, and extracts key product information.

    Args:
        url (str): The URL of the product page to scrape.

    Returns:
        str: A JSON string containing the extracted product data or an error message.
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=20000)

            # --- Product Title ---
            try:
                title_locator = page.locator('h1')
                product_name = await title_locator.inner_text()
            except Exception as e:
                print(f"Could not extract title: {e}")
                product_name = 'N/A'

            # --- Product Description ---
            try:
                # This is a guess for a rich description/detail section
                desc_locator = page.locator('div#product-detail')
                raw_description = await desc_locator.inner_text()
            except Exception as e:
                print(f"Could not extract description: {e}")
                raw_description = 'N/A'

            # --- Product Price ---
            try:
                # This locator is a guess for Alibaba's complex price structure
                price_locator = page.locator('[class*="price--original--"], [class*="price--promotion--"], [class*="price-text"]').first
                price = await price_locator.inner_text()
            except Exception as e:
                print(f"Could not extract price: {e}")
                price = 'N/A'

            # --- Product Image URLs ---
            try:
                image_urls = []
                # This locator is a guess for the main image gallery
                image_locators = page.locator('div[class*="gallery-main"] img, div[class*="image-viewer"] img')
                for i in range(await image_locators.count()):
                    src = await image_locators.nth(i).get_attribute('src')
                    if src:
                        image_urls.append(src)
            except Exception as e:
                print(f"Could not extract images: {e}")
                image_urls = []

            # --- Product Specifications ---
            try:
                specifications = {}
                # This locator is a guess for a specifications table
                spec_rows = page.locator('div[id*="spec"] tr')
                for i in range(await spec_rows.count()):
                    key_locator = spec_rows.nth(i).locator('td').nth(0)
                    value_locator = spec_rows.nth(i).locator('td').nth(1)
                    if await key_locator.count() > 0 and await value_locator.count() > 0:
                        key = await key_locator.inner_text()
                        value = await value_locator.inner_text()
                        if key and value:
                            specifications[key.strip()] = value.strip()
            except Exception as e:
                print(f"Could not extract specifications: {e}")
                specifications = {}

            await browser.close()

            product_data = {
                'product_url': url,
                'product_name': product_name.strip(),
                'raw_description': raw_description.strip(),
                'price': price.strip(),
                'image_urls': image_urls,
                'specifications': specifications,
            }

            return json.dumps(product_data, indent=2)

    except Exception as e:
        return json.dumps({"error": f"An error occurred with Playwright: {e}"}, indent=2)

