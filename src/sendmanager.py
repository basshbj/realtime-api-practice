import asyncio
import json
import websockets
import uuid
from utils.mylogger import MyLogger
from utils.state import State, StateForAudio, StateForText
from src.iomanager import IOType

class SendManager():
  def __init__(self, io_type: IOType, state: State, logger: MyLogger, ws_client: websockets.ClientConnection):
    self.logger = logger
    self.io_type = io_type
    self.ws_client = ws_client

    if io_type == IOType.AUDIO:
      self.state: StateForAudio = state
    elif io_type == IOType.TEXT:
      self.state: StateForText = state


  async def send_message(self):
    if self.io_type == IOType.AUDIO:
      await self.__send_audio()
    elif self.io_type == IOType.TEXT:
      await self.__send_text()


  async def __send_audio(self):
    done = False

    while not done:
      if self.state.input_queue.empty():
        continue

      if self.state.IS_PLAYING and self.state.IS_START_SPEAKING:
        IS_START_SPEAKING = False

        self.state.output_queue.queue.clear()
        # Cancel the current response
        cancel_response = {
          "type": "response.cancel",
        }
        await self.ws_client.send(json.dumps(cancel_response))

        # Truncate response
        truncate_response = {
          "type": "conversation.item.truncate",
          "content_index": 0,
          "audio_end_ms": 0
        }
        await self.ws_client.send(json.dumps(truncate_response))

      base64_audio = await asyncio.get_event_loop().run_in_executor(None, self.state.input_queue.get)

      input_buffer_append = {
        "type": "input_audio_buffer.append",
        "audio": base64_audio,
      }

      await self.ws_client.send(json.dumps(input_buffer_append))


  async def __send_text(self):
    done = False

    while not done:
      if self.state.input_queue.empty():
        continue

      input = await asyncio.get_event_loop().run_in_executor(None, self.state.input_queue.get)

      if input.lower() == "exit":
        #done = True
        await self.ws_client.close(1000, "Close connection")

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
      
      await self.ws_client.send(json.dumps(conversation_item))

      # Request a response from the server
      response_request = {
        "type": "response.create",
        "response": {
          "modalities": ["text"]
        }
      }

      await self.ws_client.send(json.dumps(response_request))