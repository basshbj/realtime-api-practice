import asyncio
import websockets
import json
import logging
import os
import uuid
import wave
import pyaudio
import base64
import time
from dotenv import load_dotenv

# ---- Set environment ----
logging.basicConfig(
  level=logging.INFO, 
  format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

HOST_URL = f"wss://{os.getenv("AOAI_RESOURCE_NAME")}.openai.azure.com/openai/realtime?deployment={os.getenv("AOAI_GPT_4o_REALTIME")}&api-version=2024-10-01-preview"

HEADERS = {
  "api-key": os.getenv("AOAI_API_KEY")
}


# ---- Helper functions ----
async def receive_message(websocket, logger):
  done = False

  audio = pyaudio.PyAudio()
  stream = audio.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=24000,
    output=True
  )

  is_audio_playing = False
  
  final_response = ""

  while not done:
    msg = await websocket.recv()
    data = json.loads(msg)

    # To Do add logger for the response data
    logger.info(f"RECEIVE - {data["type"]}")

    match data["type"]:
      case "response.created":
        pass
      case "response.output_item.added":
        pass
      case "response.output_item.done":
        pass
      case "response.text.delta":
        final_response += data["delta"]
      case "response.text.done":
        logger.info(f"RECEIVE - FINAL RESPONSE: {final_response}")
      case "response.audio.delta":
        # if not is_audio_playing:
        #   is_audio_playing = True
        #   logger.info("RECEIVE - START AUDIO")
        #   stream.open()
        audio_data = base64.b64decode(data["delta"])
        stream.write(audio_data)
      case "response.audio.done":
        pass
        # is_audio_playing = False
        # stream.stop_stream()
        # stream.close()
      case "response.done":
        final_response = ""
        #done = True
        pass
      case "error":
        logger.error(data["type"])
        done = True


async def send_message(websocket):
  done = False

  while not done:
    user_input = await asyncio.to_thread(input, "INPUT >>> ")

    if user_input.lower() == "exit":
      #done = True
      await websocket.close(1000, "Close connection")

    # Create a new conversation item
    conversation_item = {
      "type": "conversation.item.create",
      "item": {
        "id": str(uuid.uuid4())[:32],
        "type": "message",
        "role": "user",
        "content": [{
          "type": "input_text",
          "text": user_input
        }]
      }
    }
    
    await websocket.send(json.dumps(conversation_item))

    # Request a response from the server
    response_request = {
      "type": "response.create",
      "response": {
        "modalities": ["text", "audio"]
      }
    }

    await websocket.send(json.dumps(response_request))


async def send_message_audio(websocket):
  done = False

  audio = pyaudio.PyAudio()
  sample_rate = 24000
  duration = 100
  samples = int(sample_rate * duration / 1000)
  bytes_per_sample = 2
  bytes_per_chunk = int(samples * bytes_per_sample)

  chunk_size = 1024
  format = pyaudio.paInt16
  channels = 1
  record_seconds = 500

  stream = audio.open(
    format=format,
    channels=channels,
    rate=sample_rate,
    input=True,
    frames_per_buffer=chunk_size
  )

  start_time = time.time()

  chunk_count = 0

  print("Recording...")

  #while time.time() - start_time < record_seconds:
  while True:
    data = stream.read(chunk_size)

    base64_data = base64.b64encode(data).decode("utf-8")

    chunk_count += 1

    input_buffer_append = {
      "type": "input_audio_buffer.append",
      "audio": base64_data,
    }

    await websocket.send(json.dumps(input_buffer_append))

    await asyncio.sleep(0.1)

  # stream.stop_stream()
  # stream.close()
  # audio.terminate()


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
          "type": "semantic_vad",
          "eagerness": "auto",
          #"type": "server_vad",
          "interrupt_response": True,
          # "threshold": 0.5,
          # "prefix_padding_ms": 300,
          # "silence_duration_ms": 500,
          "create_response": True
        }
      }
    }

    await websocket.send(json.dumps(session_config))

    # Create tasks for send and receive messages
    receive_task = asyncio.create_task(receive_message(websocket, logger))
    #send_task = asyncio.create_task(send_message(websocket))
    send_task = asyncio.create_task(send_message_audio(websocket))

    # Wait for all tasks to complete
    await asyncio.gather(receive_task, send_task)

if __name__ == "__main__":
  asyncio.run(main())