import asyncio
import websockets
import json
import os
import threading
import base64
from dotenv import load_dotenv
from utils.mylogger import MyLogger
from utils.state import StateForAudio
from src.iomanager import IOType, IOManager, IOAufioConfig

# ---- Set environment ----
state = StateForAudio()
logger = MyLogger("")

load_dotenv()

HOST_URL = f"wss://{os.getenv("AOAI_RESOURCE_NAME")}.openai.azure.com/openai/realtime?deployment={os.getenv("AOAI_GPT_4o_REALTIME")}&api-version=2024-10-01-preview"

HEADERS = {
  "api-key": os.getenv("AOAI_API_KEY")
}


# ---- Helper functions ----
async def receive_message(websocket, logger):
  done = False

  while not done:
    msg = await websocket.recv()
    data = json.loads(msg)

    match data["type"]:
      case "response.created":
        logger.log_receive(data["type"])
      case "input_audio_buffer.speech_started":
        IS_START_SPEAKING = True
        logger.log_receive(data["type"])
      case "input_audio_buffer.speech_stopped":
        #IS_START_SPEAKING = False
        logger.log_receive(data["type"])
      case "response.output_item.added":
        pass
      case "response.output_item.done":
        pass
      case "response.text.delta":
        state.output_queue.put(data["delta"])
      case "response.text.done":
        print("")
        logger.log_receive(data["type"])
        print("\n")
      case "response.audio.delta":
        IS_PLAYING = True
        audio_data = base64.b64decode(data["delta"])
        # output_queue.put(audio_data)

        for i in range(0, len(audio_data), IOAufioConfig.OUTPUT_CHUNK_SIZE):
          state.output_queue.put(audio_data[i:i+IOAufioConfig.OUTPUT_CHUNK_SIZE])
      case "response.audio.done":
        IS_PLAYING = False
        logger.log_receive(data["type"])
      case "response.done":
        logger.log_receive(data["type"])
      case "error":
        done = True


async def send_message(websocket):
  done = False

  while not done:
    if state.input_queue.empty():
      continue

    if state.IS_PLAYING and state.IS_START_SPEAKING:
      IS_START_SPEAKING = False

      state.output_queue.queue.clear()
      # Cancel the current response
      cancel_response = {
        "type": "response.cancel",
      }
      await websocket.send(json.dumps(cancel_response))

      # Truncate response
      truncate_response = {
        "type": "conversation.item.truncate",
        "content_index": 0,
        "audio_end_ms": 0
      }
      await websocket.send(json.dumps(truncate_response))

    base64_audio = await asyncio.get_event_loop().run_in_executor(None, state.input_queue.get)

    input_buffer_append = {
      "type": "input_audio_buffer.append",
      "audio": base64_audio,
    }

    await websocket.send(json.dumps(input_buffer_append))


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

    await websocket.send(json.dumps(session_config))

    threading.Thread(target=io_manager.get_input, daemon=True).start()
    threading.Thread(target=io_manager.set_output, daemon=True).start()

    # Create tasks for send and receive messages
    receive_task = asyncio.create_task(receive_message(websocket, logger))
    send_task = asyncio.create_task(send_message(websocket))

    # Wait for all tasks to complete
    await asyncio.gather(receive_task, send_task)

if __name__ == "__main__":
  asyncio.run(main())