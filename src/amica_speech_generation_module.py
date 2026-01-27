from datetime import datetime

from piper.voice import PiperVoice
import sounddevice as sd
import time
import numpy as np

from audio_tools import write_wav

# piper installation on macos is currently messy:
# https://github.com/rhasspy/piper/issues/395
# pip3 install onnxruntime
# pip3 install piper-phonemize-cross
# pip3 install piper-tts --no-deps

def output_thread(queues, language, logging, log_timetag):
    message_queue, log_queue = queues
    if language == "en":
        piper = PiperVoice.load("piper_models/en_US-ryan-high.onnx")
    elif language == "de":
        piper = PiperVoice.load("piper_models/de_DE-thorsten-high.onnx")
    else:
        print("Unsupported language: ", language)
        return
    if logging:
        folder = f"logs/log_{log_timetag}/"
    stream = sd.OutputStream(samplerate=piper.config.sample_rate, channels=1, dtype="int16")
    stream.start()
    while True:
        if message_queue.empty():
            time.sleep(0.1)
        else:
            answer = message_queue.get()
            if answer == "<<hlt>>":
                stream.stop()
                stream.close()
                break
            else:
                print(answer)
                start = time.time()
                speech = []
                for chunk in piper.synthesize(answer):                    
                    audio_bytes = chunk.audio_int16_bytes
                    int_data = np.frombuffer(audio_bytes, dtype=np.int16)
                    stream.write(int_data)
                    speech.append(audio_bytes)
                end = time.time()
                wav_file_name = datetime.fromtimestamp(start).strftime("%Y-%m-%d_%H-%M-%S") + "_speech_output.wav"
                if logging:
                    write_wav(folder + wav_file_name, b''.join(speech), 1, "int16", piper.config.sample_rate)
                    log_queue.put((start, end, "speech_output", (wav_file_name,)))
