"""
Main loop for AMICA.
Handles GUI, inputs, speech-to-text conversion, and interaction with other modules.
"""

import time

import multiprocessing
from multiprocessing import Process, Queue
from multiprocessing.managers import BaseManager

import cv2
import pyaudio
import librosa  # for audio downsampling
import numpy as np
import torch
import yaml
import sys

from datetime import datetime

from audio_tools import open_microphone, calc_volume, write_wav
from gui_opencv import Gui
import pygame

from amica_answering_module import answer_generation_thread
from amica_speech_generation_module import output_thread
from logging_module import logging_thread

# original openai whisper
#import whisper  # pip install openai-whisper

# huggingface whisper turbo german
# privides gpu acceleration under MacOS
from whisper_turbo_german_hv import init_whisper_turbo


# init openai-whisper
def init_whisper():
    whisper_device = "cuda" if torch.cuda.is_available() else "cpu"
    return whisper.load_model('medium').to(whisper_device)

def init_pygame_and_joystick(joystick_number=0):
    pygame.init()
    pygame.joystick.init()

    # check the number of attached joysticks
    joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
    print("found joysticks:", joysticks)

    if len(joysticks) <= 0:
        raise Exception('no joystick was found')  # TODO raise the proper exception class instead of generic exception

    j = pygame.joystick.Joystick(joystick_number)
    j.init()
    return j



if __name__ == "__main__":
    #%%%%%%%%%%% raspberry pi pico based button press registration %%%%%%%%%%%%%%%
    #'''
    import belay
    # init belay by connecting to the pico microcontroller via USB
    try:
        pico = belay.Device("/dev/ttyACM0")
        @pico.setup
        def init_raspi_pico():
            from machine import Pin
            """Setup function to initialize the button pin on the pico."""
            # circuit is set up so that the pin reads HIGH when the button is pressed
            button = Pin(22, Pin.IN, Pin.PULL_DOWN)
        
        init_raspi_pico()
        
        @pico.task
        def button_pressed(key):
            """Returns True if the button is currently pressed, False otherwise. """
            # button.value() returns 1 if pin is HIGH, 0 if LOW
            return button.value() == 1        
    except Exception:
        print("raspberry pi pico not found. emulating PTT button press with space-bar.")
        # if no raspi pico is ar hand, 
        # use opencv to simulate key-down and key-up events by 
        # pressing and releasing the space key
        t_keypressed = time.time()
        def button_pressed(key):
            global t_keypressed
            # if space key (keycode=32) is beeing kept pressed,
            # the keyboard will repeatedly generate an event (keyrepeat time is defined by OS, typically 33ms).
            # if no new key event was generated for some time, the recording state will be set to false again.
            if key == 32:  # spacebar
                t_keypressed = time.time()
                return True
        
            if time.time() - t_keypressed > 0.5:  # 500ms after releasing the space bar: stop recording
                return False
            else:
                return True                
    finally:
        pass
    
    

    #'''
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    global_start = time.time()

    config_file = "config.yaml"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    # Load configuration from YAML
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Configuration file {config_file} not found. Exiting.")
        exit(1)

    # Assign variables from the config
    remote_ollama_server = config['remote_ollama_server']
    logging = config['logging']
    assets = config['assets']
    model_parameters = config['model_parameters']
    language = model_parameters["language"]  # extract language from model_parameters tuple

    joystick_found = False
    try:
        joystick = init_pygame_and_joystick(joystick_number=0)
        joystick_found = True
    except Exception as e:
        print("Exception:", e)

    if remote_ollama_server:
        class QueueManager(BaseManager):
            pass

        QueueManager.register('get_query_queue')
        QueueManager.register('get_answer_queue')
        QueueManager.register('get_log_queue')

        # m = QueueManager(address=('jetsonorin.local', 5000), authkey=b'abracadabra')
        # m = QueueManager(address=('ada6000.local', 5000), authkey=b'abracadabra')
        m = QueueManager(address=('Mac-mini-von-itgeiwi-admin.local', 5000), authkey=b'abracadabra')
        connected = False
        for _ in range(20):
            try:
                m.connect()
                connected = True
                print("connected to server")
                break
            except ConnectionRefusedError:
                print("Connection refused, retrying...")
                time.sleep(1)
            except Exception as e:
                print("Exception:", e)
                time.sleep(1)
        if not connected:
            print("Failed to connect to server after 20 attempts.")
            exit(1)

        query_queue = m.get_query_queue()
        answer_queue = m.get_answer_queue()
        log_queue = m.get_log_queue()
        query_queue.put("<<clr>>")
    else:
        # set start method to spawn to allow CUDA to work with multiprocessing
        multiprocessing.set_start_method('spawn')

        query_queue = Queue()
        answer_queue = Queue()
        log_queue = Queue()
        queues = (query_queue, answer_queue, log_queue)

        answer_process = Process(target=answer_generation_thread, args=(queues, assets, model_parameters))
        answer_process.start()

    timetag = time.strftime("%Y-%m-%d_%H-%M-%S")
    if logging:
        log_process = Process(target=logging_thread, args=(log_queue, global_start, timetag))
        log_process.start()
        log_queue.put((global_start, global_start+0.001, "logging_start", (0,)))

    output_queue = Queue()
    output_process = Process(target=output_thread, args=((output_queue, log_queue), language, logging, timetag))
    output_process.start()

    #whisper_model = init_whisper()
    whisper_model = init_whisper_turbo()

    print('*********************************')
    device_name = 'default'
    # device_name = 'C505e' # webcam.
    # device_name = 'StreamCam'
    # device_name = 'USB Audio Device'
    channels = 1
    audio_format = pyaudio.paInt16
    chunk_size = 1024  # number of audio samples collected by stream.read. smaller buffer, quicker response but less accurate average volume calculation..
    sample_rate = 48000  # 16000  # some devices support only specific sample rates. try 8000, 16000, 24000 and 48000
    audio = pyaudio.PyAudio()
    wav_data = []
    do_record = False
    do_speech_to_text = False
    gui = Gui(fullscreen=True)
    # gui = Gui(fullscreen=False)
    generating_answer = False
    conversation = []
    # '''
    # staged conversation for prototyping purposes
    # conversation = [
    #     'What is the moon?',
    #     'The Moon is Earths only natural satellite. It orbits at an average distance of 384,400 km, about 30 times the diameter of Earth. Tidal forces between Earth and the Moon have synchronized the Moons orbital period with its rotation period at 29.5 Earth days, causing the same side of the Moon to always face Earth.',
    #     'Can OpenCV draw things?',
    #     'OpenCV provides functionality to draw geometric shapes such as line, rectangle, circle, etc. The polylines function can be used for drawing polyline. It is a continuous line composed of one or more line segments.',
    #     'What does can OpenCVs GaussianBlur do?',
    #     'OpenCV has the "GaussianBlur" function that allows to apply Gaussian blurring on image. Smoothing is controlled by using 3 parameters, such as kernel size (ksize) and standard deviation in the X (sigmaX) and Y (sigmaY) directions. If only sigmaX is set, then sigmaY will be the same as sigmaX. If both parameters sigmaX and sigmaY are set to zeros, then they are calculated from the kernel size.']
    # '''

    # initialize some variables to avoid error messages in code editors
    start_of_speech = 0
    end_of_speech = 0
    last_interaction = 0
    reset_time = 300  # 5 minutes
    do_reset = False

    try:
        print('trying to open microphone:', device_name)
        stream = open_microphone(audio, device_name, False, chunk_size, sample_rate)

        frames = []
        t1 = time.time()
        input_level = 0
        while True:
            data = stream.read(chunk_size, exception_on_overflow=False)  # https://stackoverflow.com/questions/10733903/pyaudio-input-overflowed/
            if do_record:
                wav_data.append(data)

            # input_level = calc_volume(data)
            input_level = 0.7 * input_level + 0.3 * calc_volume(data)  # some low pass filtering to reduce bar jitter
            # print("input_level=", input_level)

            # logic to detect recording state. either using a joystick button press or the space bar
            key = cv2.waitKey(10)  # important. always call to process opencv events, otherwise the opencv-window won't redraw.
            if key == 27:  # esc key
                t = time.time()
                log_queue.put((t, t+0.001, "logging_end", (0,)))
                cv2.destroyAllWindows()
                while not output_queue.empty():
                    output_queue.get()
                output_queue.put("<<hlt>>")
                output_process.join()
                if logging:
                    log_process.join()
                if remote_ollama_server:
                    query_queue.put("<<clr>>")
                else:
                    query_queue.put("<<hlt>>")
                    answer_process.join()
                break
            elif key == 255:  # del key
                conversation = []
                query_queue.put("<<clr>>")
                while not output_queue.empty():
                    output_queue.get()
                log_queue.put((time.time(), time.time()+0.001, "clear conversation", (0,)))

            if do_reset and time.time() - last_interaction > reset_time:
                conversation = []
                query_queue.put("<<clr>>")
                while not output_queue.empty():
                    output_queue.get()
                do_reset = False
                log_queue.put((time.time(), time.time()+0.001, "clear conversation (timeout)", (0,)))
            # draw the user interface
            gui.draw(input_level, do_record, conversation, language)

            if do_speech_to_text:
                if len(wav_data) > 30:
                    start_of_transcription = time.time()
                    wav = b''.join(wav_data)

                    # do logging and save audio input as wav file
                    if logging:
                        wav_file_name = datetime.fromtimestamp(start_of_speech).strftime("%Y-%m-%d_%H-%M-%S") + "_speech_input.wav"
                        write_wav(f"logs/log_{timetag}/{wav_file_name}", wav, channels, audio_format, sample_rate)
                        log_queue.put((start_of_speech, end_of_speech, "speech_input", (wav_file_name,)))

                    # https://stackoverflow.com/questions/76779669/how-to-convert-any-audio-file-to-np-ndarray-for-openai-whisper
                    if audio_format == pyaudio.paInt16:
                        wav_np = np.frombuffer(wav, np.int16).flatten().astype(np.float32) / 32768.0
                    else:
                        raise "todo: implement alternative audio format conversions."

                    ##### whisper ####
                    # https://amgadhasan.substack.com/p/whisper-how-to-create-robust-asr-46b
                    # whisper expects the audio samples to be mono with 16 khz sampling rate.
                    if sample_rate != 16000:
                        print('resampling start')
                        t = time.time()
                        wav_np_16khz = librosa.resample(wav_np, orig_sr=sample_rate, target_sr=16000)
                        print('resampling time [s]:', time.time() - t)
                    else:
                        wav_np_16khz = wav_np

                    print('whisper start')
                    t = time.time()

                    '''
                    # original openai whisper:
                    wav_np_16khz = whisper.pad_or_trim(wav_np_16khz)
                    whisper_prompt = "Prof. Ressel, Hochschule Rhein-Waal, Amica"
                    result = whisper_model.transcribe(
                        audio=wav_np_16khz,
                        language=language,
                        task='transcribe',
                        word_timestamps=True,                   # boolean to include word timestamps and per word confidence score in the output
                        initial_prompt=whisper_prompt           # list of hard to understand words to help whisper
                    )
                    #'''

                    # hugging face whisper turbo german:
                    result = whisper_model(wav_np_16khz)

                    end_of_transcription = time.time()
                    print('whisper time [s]:', end_of_transcription - t)
                    query = result['text']
                    ## segments = [segment["words"] for segment in result["segments"]]
                    # segments = result["segments"] #  TODO: what / where are the segments for whisper turbo??
                    segments = []
                    print(query)
                    # print(segments)
                    if len(query) > 1:
                        if query[0] == " ":
                            query = query[1:]
                        log_queue.put((start_of_transcription, end_of_transcription, "speech-to-text", (query, segments)))
                        query_queue.put(query)
                        conversation.append(query)
                        conversation.append("")
                        generating_answer = True

                    ##################
                    wav_data = []
                else:
                    print("too little audio data captured for speech to text conversion")
                do_speech_to_text = False

            if generating_answer:
                if answer_queue.empty():
                    pass
                    # time.sleep(0.1) # no sleep in mainloop - enough CPU-friendly sleeping is done by cv2.waitKey(1)
                else:
                    answer = answer_queue.get()
                    if answer == "<<end of answer>>":
                        generating_answer = False
                    else:
                        output_queue.put(answer)
                        conversation[-1] += answer
            else:
                if joystick_found == True:
                    # process events. e.g. button presses
                    for event in pygame.event.get():
                        if event.type == pygame.JOYBUTTONDOWN:
                            do_record = True
                            do_speech_to_text = False
                            start_of_speech = time.time()
                        if event.type == pygame.JOYBUTTONUP:
                            do_record = False
                            do_speech_to_text = True
                            end_of_speech = time.time()
                else:
                    
                    # switch from idle state to recording state
                    if button_pressed(key) and not do_record:
                        # t1 = time.time()
                        # if do_record == False:
                        start_of_speech = time.time()
                        do_record = True
                        do_speech_to_text = False
                        do_reset = False

                    # switch from recording state to processing state
                    if not button_pressed(key) and do_record:
                        do_record = False
                        do_speech_to_text = True
                        end_of_speech = time.time()
                        last_interaction = time.time()
                        do_reset = True
        # close audio stream before exiting the script
        stream.stop_stream()
        stream.close()

    except Exception as e:
        print("Exception:", e)
    finally:
        audio.terminate()
        cv2.destroyAllWindows()

