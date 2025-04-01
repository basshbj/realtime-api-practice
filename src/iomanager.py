import queue
import pyaudio
import base64

from enum import Enum
from utils.mylogger import MyLogger
from utils.state import State, StateForAudio, StateForText

class IOType(Enum):
  TEXT = 0,
  AUDIO = 1


class IOAufioConfig:
  # Audio Input Settings
  INPUT_FORMAT = pyaudio.paInt16
  INPUT_CHANNELS = 1
  INPUT_RATE = 24000
  INPUT_CHUNK_SIZE = 1024

  # Audio Output Settings
  OUTPUT_FORMAT = pyaudio.paInt16
  OUTPUT_CHANNELS = 1
  OUTPUT_RATE = 24000
  OUTPUT_CHUNK_SIZE = 1024


class IOManager:
  def __init__(self, io_type: IOType, state: State, logger: MyLogger):
    self.logger = logger
    self.io_type = io_type

    if io_type == IOType.AUDIO:
      self.state: StateForAudio = state
      self.__init_audio_streams()
    elif io_type == IOType.TEXT:
      self.state: StateForText = state
  
  def __init_audio_streams(self):
    audio = pyaudio.PyAudio()

    self.input_stream = audio.open(
      format=IOAufioConfig.INPUT_FORMAT,
      channels=IOAufioConfig.INPUT_CHANNELS ,
      rate=IOAufioConfig.INPUT_RATE,
      input=True,
      output=False,
      frames_per_buffer=IOAufioConfig.INPUT_CHUNK_SIZE,
      start=False,
    )

    self.output_stream = audio.open(
      format=IOAufioConfig.OUTPUT_FORMAT,
      channels=IOAufioConfig.OUTPUT_CHANNELS,
      rate=IOAufioConfig.OUTPUT_RATE,
      input=False,
      output=True,
      frames_per_buffer=IOAufioConfig.OUTPUT_CHUNK_SIZE,
      start=False,
    )

    self.input_stream.start_stream()
    self.output_stream.start_stream()


  def get_input(self):
    if self.io_type == IOType.AUDIO:
      self.__listen_for_audio_input()
    elif self.io_type == IOType.TEXT:
      self.__listen_for_text_input()

  
  def set_output(self):
    if self.io_type == IOType.AUDIO:
      self.__play_audio_output()
    elif self.io_type == IOType.TEXT:
      self.__display_text_input()

  
  # ---- Audio I/O ----
  def __play_audio_output(self):
    while True:
      audio_data = self.state.output_queue.get()
      
      if audio_data is None:
        continue

      self.logger.warning("PLAYING NEW AUDIO CHUNK")

      self.output_stream.write(audio_data)


  def __listen_for_audio_input(self):
    while True:
      audio_data = self.input_stream.read(IOAufioConfig.INPUT_CHUNK_SIZE, exception_on_overflow=False)
      
      if audio_data is None:
        continue

      base64_audio = base64.b64encode(audio_data).decode("utf-8")
      self.state.input_queue.put(base64_audio)


  # ---- Text I/O ----
  def __display_text_input(self):
    while True:
      if not self.state.output_queue.empty():
        output = self.state.output_queue.get()
        print(output, end="", flush=True)    


  def __listen_for_text_input(self):
    while True:
      user_input = input("")
      self.state.input_queue.put(user_input)
