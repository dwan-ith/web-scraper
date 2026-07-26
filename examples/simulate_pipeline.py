import asyncio
import os
import json
import logging
from dotenv import load_dotenv
load_dotenv()

from app.core.scraper.har_analyzer import HarAnalyzer
from app.core.ai.reverse_engineer import AIReverseEngineer
from app.core.scraper.engine import ExecutionEngine

logging.basicConfig(level=logging.INFO)

# 1. Create a synthetic HAR that simulates a user visiting dummyjson.com
SYNTHETIC_HAR = {
    "log": {
        "entries": [
            # Noise Request 1: Image
            {
                "request": {
                    "method": "GET",
                    "url": "https://dummyjson.com/image.png",
                    "headers": [{"name": "User-Agent", "value": "Chrome"}]
                },
                "response": {
                    "status": 200,
                    "content": {"mimeType": "image/png", "size": 9000, "text": ""}
                }
            },
            # Target Data Request: Product search endpoint
            {
                "request": {
                    "method": "GET",
                    "url": "https://dummyjson.com/products/search?q=laptop",
                    "headers": [
                        {"name": "Accept", "value": "application/json"},
                        {"name": "User-Agent", "value": "Chrome"},
                        {"name": "Authorization", "value": "Bearer fake-token-123"}
                    ]
                },
                "response": {
                    "status": 200,
                    "content": {
                        "mimeType": "application/json",
                        "size": 1250,
                        "text": json.dumps({
                            "products": [{"id": 1, "title": "Laptop", "price": 999}],
                            "total": 1, "skip": 0, "limit": 10
                        })
                    }
                }
            },
            # Noise Request 2: CSS
            {
                "request": {
                    "method": "GET",
                    "url": "https://dummyjson.com/style.css",
                    "headers": [{"name": "User-Agent", "value": "Chrome"}]
                },
                "response": {
                    "status": 200,
                    "content": {"mimeType": "text/css", "size": 1500, "text": "body { color: red }"}
                }
            }
        ]
    }
}


async def main():
    print("=== ERA 3: NETWORK LAYER REVERSE ENGINEERING E2E TEST ===")
    
    # 1. Distill HAR
    print("\n[1] Distilling network traffic...")
    analyzer = HarAnalyzer(max_response_preview=500)
    distilled = analyzer.process_har(SYNTHETIC_HAR)
    print(f"    Raw HAR requests: {len(SYNTHETIC_HAR['log']['entries'])}")
    print(f"    Filtered API candidates: {len(distilled)}")

    # 2. LLM Reverse Engineer
    print("\n[2] LLM analyzing HAR context (DeepSeek mode)...")
    ai = AIReverseEngineer()
    goal = "Find the exact API request that searches for products as JSON. I want to search for phones."
    
    endpoint = await ai.identify_api(distilled, goal)
    
    print(f"\n✅ LLM Found Endpoint: {endpoint.target_url}")
    print(f"   Confidence: {endpoint.confidence}")
    print(f"   Reasoning: {endpoint.reasoning}")

    code = endpoint.to_python_function()
    print("\n--- GENERATED PYTHON FUNCTION ---")
    print(code)
    print("---------------------------------")

    # 3. Execution (Parse.bot code-mode)
    print("\n[3] Executing parsed code live against dummyjson...")
    engine = ExecutionEngine()
    
    # We substitute the interpolation token the LLM chose
    result = await engine.execute_generated_code(endpoint, variables={"search_term": "apple"})
    
    print("\n✅ Execution Result:")
    if result["success"]:
        # print first product to prove it hit the live API
        data = result.get("data", {})
        products = data.get("products", [])
        if products:
            print(f"Success! Found {data.get('total')} items. First item: {products[0].get('title')}")
        else:
            print("Response:", data)
    else:
        print("Failed:", result)


if __name__ == "__main__":
    asyncio.run(main())
