# Amica: A privacy-friendly voice assistant for school children. 



## Menu: [Installation](#Installation) | [Usage](#Usage) | [Documentation](#Documentation) 

## Installation

### prerequisites:
python version:  >= 3.12 (default on linux mint 22)


The required package **pyaudio** depends on the c(++) library portaudio.
The development header files and libraries for portaudio should be installed before installing the python requirements:

```
sudo apt install portaudio19-dev
```

now install the required python libs:
```
pip -r requirements.txt
```


### MacOS specific steps

TODO - describe in more detail.. 

https://stackoverflow.com/questions/33851379/how-to-install-pyaudio-on-mac-using-python-3#33851618

```
xcode-select --install
brew remove portaudio
brew install portaudio
brew install font-liberation
```

## Usage

Before starting Amica, you need to download the voice model and create the vector embeddings for the Q&A Database:
```
./download_thorsten_voice.sh
python data_packager.py
```

To start Amica, now run:
```
python amica_main_loop.py
```

Be patient, some models might be downloading on first startup.


## Documentation

### generate docs
To re-generate documentation from the python files, run:
https://www.sphinx-doc.org/en/master/usage/installation.html

```
cd docs
pip install -r requirements.txt
make html
make latexpdf
```

