import logging

RESET = "\033[0m"
COLORS = {
  'DEBUG': "\033[94m",   # Blue
  'INFO': "\033[92m",    # Green
  'WARNING': "\033[93m", # Yellow
  'ERROR': "\033[91m",   # Red
  'CRITICAL': "\033[95m" # Magenta
}

class CustomFormatter(logging.Formatter):
  def format(self, record):
    log_color = COLORS.get(record.levelname, RESET)
    message = super().format(record)
    return f"{log_color}{message}{RESET}"

class MyLogger(logging.Logger):
  def __init__(self, name, level=logging.DEBUG):
    super().__init__(name, level)
    self.setLevel(level)

    # Create console handler with custom formatter
    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = CustomFormatter("[%(levelname)s] %(message)s")
    ch.setFormatter(formatter)

    # Add the handler to the logger
    self.addHandler(ch)

  def log_send(self, message, level=logging.DEBUG):
    self.__log(f"[SEND] {message}", level)

  def log_receive(self, message, level=logging.DEBUG):
    self.__log(f"[RECEIVE] {message}", level)

  def __log(self, message, level):
    match level:
      case logging.DEBUG:
        self.debug(message)
      case logging.INFO:
        self.info(message)
      case logging.WARNING:
        self.warning(message)
      case logging.ERROR:
        self.error(message)
      case logging.CRITICAL:
        self.critical(message)
  