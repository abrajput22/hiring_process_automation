"""
Keep-alive service to prevent Render cold starts.
Sends periodic requests to keep the service warm.
"""

import asyncio
import aiohttp
import os
from datetime import datetime

RENDER_URL = os.getenv("RENDER_URL", "https://hiring-process-automation-1.onrender.com")

async def ping_service():
    """Send a simple ping to keep service alive."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{RENDER_URL}/health", timeout=5) as response:
                if response.status == 200:
                    print(f"✅ Keep-alive ping successful at {datetime.now()}")
                else:
                    print(f"⚠️ Keep-alive ping returned {response.status}")
    except Exception as e:
        print(f"❌ Keep-alive ping failed: {e}")

async def keep_alive_loop():
    """Run keep-alive pings every 10 minutes."""
    while True:
        await ping_service()
        await asyncio.sleep(600)  # 10 minutes

if __name__ == "__main__":
    asyncio.run(keep_alive_loop())