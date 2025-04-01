import queue

class State():
  input_queue = queue.Queue()
  output_queue = queue.Queue()
  tools_queue = queue.Queue()

class StateForAudio(State):  
  IS_PLAYING = False
  IS_START_SPEAKING = False


class StateForText(State):
  pass