import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def scrape_page(url: str) -> str:
    """
    Loads a webpage in a headless browser and returns its HTML.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        html = await page.content()
        await browser.close()
        return html

def extract_with_bs4(html: str, selector: str):
    """
    Extract elements matching the given CSS selector.
    Returns list of text contents.
    """
    soup = BeautifulSoup(html, "html.parser")
    elements = soup.select(selector)
    return [el.get_text(strip=True) for el in elements]
