import base64
import json
import websockets
from utils.mylogger import MyLogger
from utils.state import State, StateForAudio, StateForText
from src.iomanager import IOType, IOAufioConfig


class ReceiveManager():
  def __init__(self, io_type: IOType, state: State, logger: MyLogger, ws_client: websockets.ClientConnection):
    self.logger = logger
    self.io_type = io_type
    self.ws_client = ws_client

    if io_type == IOType.AUDIO:
      self.state: StateForAudio = state
    elif io_type == IOType.TEXT:
      self.state: StateForText = state

  
  async def receive_message(self):
    done = False

    while not done:
      msg = await self.ws_client.recv()
      data = json.loads(msg)

      self.logger.log_receive(data["type"])

      match data["type"]:
        case "conversation.created":
          pass
        case "conversation.item.created":
          pass
        case "conversation.item.deleted":
          pass
        case "conversation.item.input_audio_transcription.completed":
          pass
        case "conversation.item.input_audio_transcription.failed":
          pass
        case "conversation.item.truncated":
          pass
        case "input_audio_buffer.cleared":
          pass
        case "input_audio_buffer.committed":
          pass
        case "input_audio_buffer.speech_started":
          self.state.IS_START_SPEAKING = True
        case "input_audio_buffer.speech_stopped":
          self.state.IS_START_SPEAKING = False
        case "rate_limits.updated":
          pass
        case "response.audio.delta":
          self.state.IS_PLAYING = True
          audio_data = base64.b64decode(data["delta"])

          for i in range(0, len(audio_data), IOAufioConfig.OUTPUT_CHUNK_SIZE):
            self.state.output_queue.put(audio_data[i:i+IOAufioConfig.OUTPUT_CHUNK_SIZE])
        case "response.audio.done":
          self.state.IS_PLAYING = False
        case "response.audio_transcript.delta":
          pass
        case "response.audio_transcript.done":
          pass
        case "response.content_part.added":
          pass
        case "response.content_part.done":
          pass
        case "response.created":
          pass
        case "response.done":
          pass
        case "response.function_call_arguments.delta":
          pass
        case "response.function_call_arguments.done":
          pass
        case "response.output_item.added":
          pass
        case "response.output_item.done":
          pass
        case "response.text.delta":
          self.state.output_queue.put(data["delta"])
        case "response.text.done":
          self.state.output_queue.put("\n")
        case "session.created":
          pass
        case "session.updated":
          pass
        case "error":
          self.logger.error(data["error"]["message"])