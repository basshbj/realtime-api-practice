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
    last_item_id = None

    # Wait for session to be created
    msg = await ws_client.recv()
    data = json.loads(msg)
    session_id = data["session"]["id"]

    print(data)
    logger.info(data["type"])
    logger.info(f"Session ID: {session_id}")

    # Configure Session
    # Set modalities and system prompt (instructions)
    await ws_client.send(json.dumps(
      {
        "type": "session.update",
        "session": {
          "modalities": ["text"],
          "instructions": "Answer all the questions in a friendly manner. And add some emojis to the end of the answer.",
        }
      })
    )


    while True:
      user_input = input("Enter your message: ")
      if user_input == "exit":
        await ws_client.close(1000, "Close connection")

      # Add message to the conversation history
      await ws_client.send(json.dumps(
        {
          "type": "conversation.item.create",
          "item": {
            "id": str(uuid.uuid4())[:32],
            "type": "message",
            "role": "user",
            "content": [{
              "type": "input_text",
              "text": user_input
            }]
          },
          "previous_item_id": last_item_id,
        })
      )

      # Wait for item created confirmation
      while True:
        msg = await ws_client.recv()
        data = json.loads(msg)

        match data["type"]:
          case "conversation.item.created":
            last_item_id = data["item"]["id"]

        if data["type"] == "conversation.item.created":
          last_item_id = data["item"]["id"]
          break
      

      # Request response from the server
      await ws_client.send(json.dumps({
        "type": "response.create",
        "response": {
          "modalities": ["text"],
        }
      }))


      # Wait for response
      done = False
      while not done:
        msg = await ws_client.recv()
        data = json.loads(msg)

        match data["type"]:
          case "response.done":
            done = True
            print("\n")
          case " response.text.delta":
            # Use this to stream the response
            print(data["delta"], end="")
          case "error":
            done = True
            logger.error(data["error"])


if __name__ == "__main__":
  asyncio.run(main())