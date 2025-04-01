import asyncio
import websockets
import json
import os
import uuid
import queue
import threading
import pyaudio
import base64
import time
from dotenv import load_dotenv
from utils.mylogger import MyLogger

# ---- Set environment ----
logger = MyLogger("")

load_dotenv()

HOST_URL = f"wss://{os.getenv("AOAI_RESOURCE_NAME")}.openai.azure.com/openai/realtime?deployment={os.getenv("AOAI_GPT_4o_REALTIME")}&api-version=2024-10-01-preview"

HEADERS = {
  "api-key": os.getenv("AOAI_API_KEY")
}

input_queue = queue.Queue()
output_queue = queue.Queue()


# ---- I/O Settings ----
# Input
INPUT_FORMAT = pyaudio.paInt16
INPUT_CHANNELS = 1
INPUT_RATE = 24000
INPUT_CHUNK_SIZE = 1024

# Output
OUTPUT_FORMAT = pyaudio.paInt16
OUTPUT_CHANNELS = 1
OUTPUT_RATE = 24000
OUTPUT_CHUNK_SIZE = 1024


# ---- Gloval variables ----
IS_PLAYING = False
IS_START_SPEAKING = False


# ---- Input/Output ----
def play_output(output_stream):
  while True:
    audio_data = output_queue.get()
    
    if audio_data is None:
      continue

    logger.warning("PLAYING NEW AUDIO CHUNK")

    output_stream.write(audio_data)

def listen_for_input(input_stream):
  while True:
    audio_data = input_stream.read(INPUT_CHUNK_SIZE, exception_on_overflow=False)
    
    if audio_data is None:
      continue

    base64_audio = base64.b64encode(audio_data).decode("utf-8")
    input_queue.put(base64_audio)


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
        output_queue.put(data["delta"])
      case "response.text.done":
        print("")
        logger.log_receive(data["type"])
        print("\n")
      case "response.audio.delta":
        IS_PLAYING = True
        audio_data = base64.b64decode(data["delta"])
        # output_queue.put(audio_data)

        for i in range(0, len(audio_data), OUTPUT_CHUNK_SIZE):
          output_queue.put(audio_data[i:i+OUTPUT_CHUNK_SIZE])
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
    if input_queue.empty():
      continue

    if IS_PLAYING and IS_START_SPEAKING:
      IS_START_SPEAKING = False

      output_queue.queue.clear()
      # Cancel the current response
      cancel_response = {
        "type": "response.cancel",
      }
      await websocket.send(json.dumps(cancel_response))

      # Truncate response
      truncate_response = {
        "type": "conversation.item.truncate",
        #"item_id": "<item_id>",
        "content_index": 0,
        "audio_end_ms": 0
      }
      await websocket.send(json.dumps(truncate_response))

    base64_audio = await asyncio.get_event_loop().run_in_executor(None, input_queue.get)

    input_buffer_append = {
      "type": "input_audio_buffer.append",
      "audio": base64_audio,
    }

    await websocket.send(json.dumps(input_buffer_append))

    #await asyncio.sleep(0.1)


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

    audio = pyaudio.PyAudio()

    input_stream = audio.open(
        format=INPUT_FORMAT,
        channels=INPUT_CHANNELS ,
        rate=INPUT_RATE,
        input=True,
        output=False,
        frames_per_buffer=INPUT_CHUNK_SIZE,
        start=False,
    )

    output_stream = audio.open(
        format=OUTPUT_FORMAT,
        channels=OUTPUT_CHANNELS,
        rate=OUTPUT_RATE,
        input=False,
        output=True,
        frames_per_buffer=OUTPUT_CHUNK_SIZE,
        start=False,
    )

    input_stream.start_stream()
    output_stream.start_stream()

    await websocket.send(json.dumps(session_config))

    threading.Thread(target=listen_for_input, args=(input_stream,), daemon=True).start()
    threading.Thread(target=play_output, args=(output_stream,), daemon=True).start()

    # Create tasks for send and receive messages
    receive_task = asyncio.create_task(receive_message(websocket, logger))
    send_task = asyncio.create_task(send_message(websocket))

    # Wait for all tasks to complete
    await asyncio.gather(receive_task, send_task)

if __name__ == "__main__":
  asyncio.run(main())