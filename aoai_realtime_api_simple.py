import asyncio
import websockets
import json
import logging
import os
import uuid
from dotenv import load_dotenv

# Set environment
logging.basicConfig(
  level=logging.INFO, 
  format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

AOAI_RESOURCE_NAME = os.getenv("AOAI_RESOURCE_NAME")
AOAI_GPT_4o_REALTIME = os.getenv("AOAI_GPT_4o_REALTIME")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")

HOST_URL = f"wss://{AOAI_RESOURCE_NAME}.openai.azure.com/openai/realtime?deployment={AOAI_GPT_4o_REALTIME}&api-version=2024-10-01-preview"

HEADERS = {
  "api-key": AOAI_API_KEY
}


# APP
async def main():
  # Connect to WebSocket server
  async with websockets.connect(HOST_URL, additional_headers=HEADERS) as ws_client:
    logger.info("Connected to AOAI WebSocket")
    
    session_id = None
    # conversation_history = []
    last_item_id = None

    # Wait for session to be created
    msg = await ws_client.recv()
    data = json.loads(msg)
    print(data)
    logger.info(data["type"])
    session_id = data["session"]["id"]
    logger.info(f"Session ID: {session_id}")

    # Set System prompt
    await ws_client.send(json.dumps(
      {
        "type": "session.update",
        "session": {
          "modalities": ["text"],
          "instructions": "Answer all the questions in a friendly manner. And add some emojis to the end of the answer.",
        }
      })
    )

    turn = 1

    while True:
      user_input = input("Enter your message: ")
      if user_input == "exit":
        await ws_client.close(1000, "Close connection")
      
      user_msg_id = str(uuid.uuid4())[:32]

      # Add message to the conversation history
      await ws_client.send(json.dumps(
        {
          "type": "conversation.item.create",
          "item": {
            "id": user_msg_id,
            "type": "message",
            "role": "user",
            "content": [{
              "type": "input_text",
              "text": user_input
            }]
          }
        })
      )

      # Wait for item created confirmation
      # while True:
      #   msg = await ws_client.recv()
      #   data = json.loads(msg)
      #   if data["type"] == "conversation.item.created":
      #     last_item_id = data["item"]["id"]
      #     break
      

      # Request response from the server
      await ws_client.send(json.dumps({
        "type": "response.create",
        "response": {
          "modalities": ["text"],
        }
      }))

      # Wait for response
      response_text = ""
      while True:
        msg = await ws_client.recv()
        data = json.loads(msg)
        if data["type"] == "response.done":
          break
        elif data["type"] == "response.text.delta":
          response_text += data["delta"]
        elif data["type"] == "error":
          print(f"Error: {data['error']}")
          break

      # Print the response
      print(f"Response: {response_text}")
      turn += 1


if __name__ == "__main__":
  asyncio.run(main())