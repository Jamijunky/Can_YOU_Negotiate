import os
import asyncio
from dotenv import load_dotenv
load_dotenv()
from livekit.plugins.rime import TTS
async def test_tts():
    tts = TTS(model="mistv3", speaker="cove")
    stream = tts.synthesize("This is a test.")
    async for chunk in stream:
        print("Got audio chunk:", len(chunk.data))
    print("Done")
asyncio.run(test_tts())
