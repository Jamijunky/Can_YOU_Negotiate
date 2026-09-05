import os
from dotenv import load_dotenv
import asyncio
load_dotenv()

from livekit.plugins.google.tts import TTS
from google.api_core.client_options import ClientOptions
from livekit.agents.tts import SynthesizeStream

# Monkey patch ClientOptions
_orig_init = ClientOptions.__init__
def patched_init(self, *args, **kwargs):
    kwargs['api_key'] = os.environ.get("GOOGLE_API_KEY")
    _orig_init(self, *args, **kwargs)
ClientOptions.__init__ = patched_init

async def test_tts():
    tts = TTS(voice_name="en-US-Journey-D")
    stream = tts.synthesize("This is a test of the google TTS API.")
    async for chunk in stream:
        print("Got audio chunk:", len(chunk.data))
    
if __name__ == "__main__":
    asyncio.run(test_tts())
