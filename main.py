from fastapi import FastAPI, HTTPException
from scraper import scrape_page, extract_with_bs4

app = FastAPI()

@app.post("/run-scraper")
async def run_scraper(payload: dict):
    url = payload.get("url")
    selector = payload.get("selector")

    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url'")
    if not selector:
        raise HTTPException(status_code=400, detail="Missing 'selector'")

    try:
        html = await scrape_page(url)
        data = extract_with_bs4(html, selector)
        return {"url": url, "selector": selector, "results": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

