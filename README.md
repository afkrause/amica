# AMICA: a friendly, privacy-respecting voice assistant

## Menu: [Installation](#Installation) | [Usage](#Usage) | [Documentation](#Documentation) 

## Introduction
AMICA = Accessible Multimodal Interaction Conversational Assistant
- customized for German-speaking school children (with Intellectual Disabilities),
- with our design principle of **100% privacy, 0% cloud**,
- therefore can be adapted to become a privacy-friendly voice assistant for anyone concerned about data protection and confidentiality.

### related publication
If you would like to cite AMICA, please use:

Krause, A. F., Savelov, A., Ching, C., Kannen, K., Pitsch, K., Wild-Wall, N. & Ressel, C. (forthcoming). AMICA: Accessible Multimodal Interaction Conversational Assistant
for School Children with Intellectual Disabilities. In The Eighteenth International Conference on Advanced Cognitive Technologies and Applications, (COGNITIVE 2026) (accepted)

A paper for this work was peer-reviewed and accepted by [COGNITIVE 2026](https://www.iaria.org/conferences2026/CfPCOGNITIVE26.html). The paper link will be included here after publication.



![GUI Background Image](https://github.com/afkrause/amica/blob/main/assets/mystical_llama_by_saiyagina_d2muhab.jpg)
*Credits: Georgina Chacón, ["Mystical Llama"](https://www.deviantart.com/saiyagina/art/Mystical-Llama-159305987) (CC BY-NC-ND 3.0 License)*


## Installation

### prerequisites
Python version:  >= 3.12 (default on Linux Mint 22)


The required package **pyaudio** depends on the C(++) library **portaudio**.
The development header files and libraries for portaudio should be installed before installing the Python requirements:

```
sudo apt install portaudio19-dev
```

now install the required Python libs:
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

Before starting AMICA, you need to download the voice model: 

```
./download_thorsten_voice.sh
```

and create the vector embeddings for the Q&A Database:
```
python src/data_packager.py
```
or
```
uv run src/data_packager.py
```

To start AMICA, now run:
```
python src/amica_main_loop.py
```
or
```
uv run src/amica_main_loop.py
```

Be patient, some models and data files need to be loaded during startup. 
Do not press the microphone button before the message "vector store loaded" appears in the command line.


## Documentation

### to generate docs
To re-generate documentation from the Python files, run:
https://www.sphinx-doc.org/en/master/usage/installation.html

```
cd docs
pip install -r requirements.txt
make html
make latexpdf
```


## Acknowledgments
This work was supported by the Ministry of Culture and Science of the State of North Rhine-Westphalia as part of the project "Center for Assistive Technology Rhine-Ruhr" (ZAT) (11/2023 to 10/2026, Grant No. PB22-076A and PB22-076D).

We thank Aaron Schneider and Seetu Shrestha from the Rhine-Waal University of Applied Sciences for their support in conducting pilot study 2.
We thank Felix Bergmann, Anne Ferger and Thomas Schmidt from the University of Duisburg-Essen for supporting the data management of study 1.

*Source Code Availability and Licenses*

The source code of AMICA is released under the GNU General Public License, version 3 (GPL‑3.0).
We thank Georgina Chacón for granting permission to use her artwork ["Mystical Llama"](https://www.deviantart.com/saiyagina/art/Mystical-Llama-159305987) (CC BY-NC-ND 3.0 License) as the background image of AMICA's GUI.
