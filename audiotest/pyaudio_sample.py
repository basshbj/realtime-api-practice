import wave
import sys
import pyaudio
import threading
import time
# from pydub import AudioSegment
# from pydub.playback import play

# def play_audio_with_pydub(file_path):
#   try:
#     # Load the audio file
#     audio = AudioSegment.from_mp3(file_path)
    
#     # Play the audio
#     play(audio)
#   except Exception as e:
#     print(f"An error occurred: {e}")


def play_audio_with_pyaudio():
  file_path = "assests/sample1.wav"
  try:
    CHUNK_SIZE = 1024

    with wave.open(file_path, 'rb') as wf:
      p = pyaudio.PyAudio()
      print(f"Channels: {wf.getnchannels()}")
      stream = p.open(
        format=p.get_format_from_width(wf.getsampwidth()),
        channels=wf.getnchannels(),
        rate=wf.getframerate(),
        output=True
      )

      # Play the audio
      while len(data := wf.readframes(CHUNK_SIZE)) > 0:
        # Write the audio data to the stream
        stream.write(data)

      # Stop and close the stream
      stream.stop_stream()
      stream.close()
      p.terminate()
  except Exception as e:
    print(f"An error occurred: {e}")
    

def record_audio_with_pyaudio():
  file_path = "assests/result1.wav"
  try:
    CHUNK_SIZE = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = 7

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK_SIZE)

    print("Recording...")
    frames = []

    for _ in range(0, int(RATE / CHUNK_SIZE * RECORD_SECONDS)):
      data = stream.read(CHUNK_SIZE)
      frames.append(data)

    print("Finished recording.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    with wave.open(file_path, 'wb') as wf:
      wf.setnchannels(CHANNELS)
      wf.setsampwidth(p.get_sample_size(FORMAT))
      wf.setframerate(RATE)
      wf.writeframes(b''.join(frames))


  except Exception as e:
    print(f"An error occurred: {e}")


if __name__ == "__main__":
  

  record_thread = threading.Thread(target=record_audio_with_pyaudio)
  play_thread = threading.Thread(target=play_audio_with_pyaudio)

  record_thread.start()
  time.sleep(1)  # Ensure recording starts before playback
  play_thread.start()