import pyaudio
import numpy as np
import array
import wave


# opens a microphone with device name that contains the string given by the parameter name
# example: full name of internal laptop microphone: 'HDA Intel PCH: ALC256 Analog (hw:0,0)'
# substring sufficient to find the microphone: 'HDA Intel'
def open_microphone(audio, name='default', partial_match: bool = False, chunk_size: int =1024, sample_rate=48000, channels=1, audio_format=pyaudio.paInt16):
    
    info = audio.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')

    device_idx = -1

    # collect input devices
    input_devices = dict()
    print("==== audio input devices ====")
    for i in range(0, numdevices):
        if (audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            device_name = audio.get_device_info_by_host_api_device_index(0, i).get('name')
            input_devices[device_name]=i
            print("Input Device id ", i, " - ", device_name)
    
    # search for a matching device name
    for device_name in input_devices.keys():
        if device_name == name:
            device_idx = input_devices[device_name]
            break # choose the first device found. 
            
        if partial_match and name in device_name:
            device_idx = input_devices[device_name]
            break

    if device_idx == -1:
        raise Exception('no matching microphone name found')
        
    print("found a matching input device. idx=", i, ", name=", device_name)
        
    stream = audio.open(input_device_index=device_idx,
                        format=audio_format, channels=channels,
                        rate=sample_rate, input=True,
                        frames_per_buffer=chunk_size)
                        # sample_rate=RATE)
    return stream 


# calcs average volume from a 16bit audio chunk by root-mean-squaring the data
def calc_volume(data):
    data = array.array('h', data) # convert to array of signed 16bit integers
    data = np.array(data, dtype=float) # convert to float
    rms = np.sqrt(np.mean(data*data))
    return rms

def write_wav(filename, data, channels, audio_format, sample_rate):
    # write wav file
    waveFile = wave.open(filename, 'wb')
    waveFile.setnchannels(channels)
    waveFile.setsampwidth(2)
    #audio.get_sample_size(audio_format)
    waveFile.setframerate(sample_rate)
    waveFile.writeframes(data)
    waveFile.close()
