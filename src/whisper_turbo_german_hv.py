# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
# https://huggingface.co/primeline/whisper-large-v3-turbo-german

import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import time

def init_whisper_turbo():
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    # for macos m4pro:
    if torch.mps.is_available():
        device=torch.device("mps")
        torch_dtype = torch.float16 
    
    model_id = "primeline/whisper-large-v3-turbo-german"
    # low_cpu_mem_usage=True requires accelerate package
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
    )
    model.to(device)
    processor = AutoProcessor.from_pretrained(model_id)
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        max_new_tokens=128,
        chunk_length_s=30,
        batch_size=16,
        return_timestamps=True,
        torch_dtype=torch_dtype,
        device=device,
    )
    return pipe

if __name__ == "__main__":
    from datasets import load_dataset
    pipe = init_whisper_turbo()
    dataset = load_dataset("distil-whisper/librispeech_long", "clean", split="validation")
    sample = dataset[0]["audio"]
    t1 = time.time()
    result = pipe(sample)
    print("transcription time: ", time.time() - t1)
    print("result: ", result["text"])
