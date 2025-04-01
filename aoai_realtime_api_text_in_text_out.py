import asyncio
import websockets
import json
import os
import uuid
import threading
from dotenv import load_dotenv
from utils.mylogger import MyLogger
from utils.state import StateForText

# ---- Set environment ----
state = StateForText()
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
      case "response.done":
        pass
      case "error":
        done = True


async def send_message(websocket):
  done = False

  while not done:
    if state.input_queue.empty():
      continue

    input = await asyncio.get_event_loop().run_in_executor(None, state.input_queue.get)

    if input.lower() == "exit":
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
          "text": input
        }]
      }
    }
    
    await websocket.send(json.dumps(conversation_item))

    # Request a response from the server
    response_request = {
      "type": "response.create",
      "response": {
        "modalities": ["text"]
      }
    }

    await websocket.send(json.dumps(response_request))

    await asyncio.sleep(0.1)  # Add a small delay to avoid overwhelming the server


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
      }
    }

    await websocket.send(json.dumps(session_config))

    threading.Thread(target=state.get_input, daemon=True).start()
    threading.Thread(target=state.print_output, daemon=True).start()

    # Create tasks for send and receive messages
    receive_task = asyncio.create_task(receive_message(websocket, logger))
    send_task = asyncio.create_task(send_message(websocket))

    # Wait for all tasks to complete
    await asyncio.gather(receive_task, send_task)

if __name__ == "__main__":
  asyncio.run(main())