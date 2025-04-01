import asyncio
import websockets
import json
import os
import threading
from dotenv import load_dotenv
from utils.mylogger import MyLogger
from utils.state import StateForAudio
from src.iomanager import IOType, IOManager, IOAufioConfig
from src.sendmanager import SendManager
from src.receivemanager import ReceiveManager

# ---- Set environment ----
state = StateForAudio()
logger = MyLogger("")

load_dotenv()

HOST_URL = f"wss://{os.getenv("AOAI_RESOURCE_NAME")}.openai.azure.com/openai/realtime?deployment={os.getenv("AOAI_GPT_4o_REALTIME")}&api-version=2024-10-01-preview"

HEADERS = {
  "api-key": os.getenv("AOAI_API_KEY")
}

# ---- Main function ----
async def main():
  async with websockets.connect(
    HOST_URL,
    additional_headers=HEADERS
  ) as websocket:
    logger.info("Connected to AOAI WebSocket")

    session_config = {
      "type": "session.update",
      "session": {
        "modalities": ["text", "audio"],
        "instructions": "Answer all the questions in a friendly manner. And add some emojis to the end of the answer.",
        "voice": "sage",
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "input_audio_transcription": {
          "model": "whisper-1"
        },
        "turn_detection": {
          "type": "server_vad",
          "threshold": 0.5, # Default Value
          "prefix_padding_ms": 300, # Default Value
          "silence_duration_ms": 500, # Default Value
          "create_response": True # Defaul Value
        }
      }
    }

    io_manager = IOManager(IOType.AUDIO, state, logger)
    send_manager = SendManager(IOType.AUDIO, state, logger, websocket)
    receive_manager = ReceiveManager(IOType.AUDIO, state, logger, websocket)

    await websocket.send(json.dumps(session_config))

    threading.Thread(target=io_manager.get_input, daemon=True).start()
    threading.Thread(target=io_manager.set_output, daemon=True).start()

    # Create tasks for send and receive messages
    receive_task = asyncio.create_task(receive_manager.receive_message())
    send_task = asyncio.create_task(send_manager.send_message())

    # Wait for all tasks to complete
    await asyncio.gather(receive_task, send_task)

if __name__ == "__main__":
  asyncio.run(main())