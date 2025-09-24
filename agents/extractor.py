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
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)

            # --- Product Title ---
            try:
                title_locator = page.locator('h1')
                product_name = await title_locator.inner_text()
            except Exception as e:
                print(f"Could not extract title: {e}")
                product_name = 'N/A'

            # --- Product Description ---
            try:
                desc_selector = 'div#detail_decorate_root'
                await page.wait_for_selector(desc_selector, timeout=10000)
                desc_locator = page.locator(desc_selector)
                raw_description = await desc_locator.inner_text()
            except Exception as e:
                print(f"Could not extract description: {e}")
                raw_description = 'N/A'

            # --- Product Price ---
            try:
                price_data = []
                # Wait for the main price container to be visible
                price_container_selector = '[data-testid="product-price"]'
                await page.wait_for_selector(price_container_selector, timeout=10000)
                
                # Find all price items within the container
                price_items = page.locator(f'{price_container_selector} .price-item')
                
                for i in range(await price_items.count()):
                    item = price_items.nth(i)
                    # Locators are based on the HTML snippet provided
                    quantity_locator = item.locator('div.id-text-sm')
                    price_value_locator = item.locator('span')
                    
                    quantity = await quantity_locator.inner_text()
                    price_value = await price_value_locator.inner_text()
                    
                    price_data.append({
                        "quantity": quantity.strip(),
                        "price": price_value.strip()
                    })
                price = price_data
            except Exception as e:
                print(f"Could not extract structured price: {e}")
                # Fallback to old method just in case
                try:
                    price_locator = page.locator('[class*="price--original--"], [class*="price--promotion--"], [class*="price-text"]').first
                    price = await price_locator.inner_text()
                except Exception:
                    price = []

            # --- Product Image URLs ---
            try:
                image_urls = []
                # Use the same container as the description which contains all rich content
                main_content_selector = 'div#detail_decorate_root'
                await page.wait_for_selector(main_content_selector, timeout=10000)
                
                image_locators = page.locator(f'{main_content_selector} img')
                
                for i in range(await image_locators.count()):
                    src = await image_locators.nth(i).get_attribute('src')
                    if src:
                        # Ensure URL is absolute by prepending https: if it starts with //
                        if src.startswith('//'):
                            image_urls.append(f'https:{src}')
                        else:
                            image_urls.append(src)
            except Exception as e:
                print(f"Could not extract images: {e}")
                image_urls = []

            # --- Product Specifications ---
            try:
                specifications = {}
                # Wait for the attributes container to be visible
                specs_container_selector = '[data-testid="module-attribute"]'
                await page.wait_for_selector(specs_container_selector, timeout=10000)
                
                # The container for the grid of attributes
                grid_container = page.locator(f'{specs_container_selector} .id-grid.id-grid-cols-2').first
                
                # Each attribute is a div that is a direct child of the grid
                attribute_rows = grid_container.locator('> div')

                for i in range(await attribute_rows.count()):
                    row = attribute_rows.nth(i)
                    # The key and value are the two divs inside the row
                    # We take the `title` attribute as it contains the full, untruncated text
                    key_element = row.locator('div').nth(0)
                    value_element = row.locator('div').nth(1)

                    key = await key_element.get_attribute('title')
                    value = await value_element.get_attribute('title')

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
                'price': price,
                'image_urls': image_urls,
                'specifications': specifications,
            }

            return json.dumps(product_data, indent=2)

    except Exception as e:
        return json.dumps({"error": f"An error occurred with Playwright: {e}"}, indent=2)

