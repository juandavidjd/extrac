#!/usr/bin/env python3
"""Wipe store and upload via proper pipeline."""
import asyncio
import httpx
import sys
import json

async def wipe_store(shop: str, token: str):
    """Delete all products from store."""
    base_url = f"https://{shop}/admin/api/2024-01"
    headers = {"X-Shopify-Access-Token": token}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get all products
        all_ids = []
        url = f"{base_url}/products.json?limit=250"
        
        while url:
            resp = await client.get(url, headers=headers)
            data = resp.json()
            products = data.get("products", [])
            all_ids.extend([p["id"] for p in products])
            
            # Check for next page
            link = resp.headers.get("Link", "")
            if 'rel="next"' in link:
                for part in link.split(","):
                    if 'rel="next"' in part:
                        url = part.split("<")[1].split(">")[0]
                        break
            else:
                url = None
        
        print(f"Total products to delete: {len(all_ids)}")
        
        # Delete in batches
        deleted = 0
        for pid in all_ids:
            try:
                resp = await client.delete(f"{base_url}/products/{pid}.json", headers=headers)
                if resp.status_code in (200, 204):
                    deleted += 1
                    if deleted % 50 == 0:
                        print(f"  Deleted: {deleted}/{len(all_ids)}")
                await asyncio.sleep(0.5)  # Rate limit
            except Exception as e:
                print(f"  Error deleting {pid}: {e}")
        
        print(f"Wipe complete: {deleted} deleted")
        return deleted

async def main():
    store = sys.argv[1] if len(sys.argv) > 1 else 'DFG'
    
    # Load brand config
    with open(f"/opt/odi/data/brands/{store.lower()}.json") as f:
        brand = json.load(f)
    
    shop = brand["shopify"]["shop"]
    token = brand["shopify"]["token"]
    
    print(f"Wiping {store} ({shop})...")
    await wipe_store(shop, token)
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
