import json

import pandas as pd
import yaml
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

if __name__ == "__main__":

    embeddings_model = "Snowflake/snowflake-arctic-embed-l-v2.0"
    folder = "assets"
    qa_files = ["amica_qa_de.csv"]
    data_files = ["data_with_schedules.txt"]
    # load the embeddings model
    print("loading embedding model: ", embeddings_model)
    embeddings = HuggingFaceEmbeddings(model_name=embeddings_model, model_kwargs={'device': 'cpu'})

    # This code is used to take Q&A files and data files from the assets folder and to package them all into vectorstores
    # one vectorstore for questions, and one vectorstore for data files
    # Q&A is also combined into a YAML file for easy access
    # the vectorstores are saved to the assets folder for later use
    # Doing it this way allows us to use vectorstores without having to reprocess the data every time


    # create lists to hold questions and answers
    answers = []
    questions = []
    # load the questions and answers from the qa files    
    for file in qa_files:
        print("load Q&A file: ", file)
        filepath = f"{folder}/{file}"
        # check if the file is json or csv
        if file.endswith(".json"):
            with open(filepath, "r") as f:
                for line in f:
                    data = json.loads(line.strip())
                    for qa in data:
                        questions.append(qa[f"Question"])
                        answers.append(qa[f"Answer"])
        elif file.endswith(".csv"):
            data = pd.read_csv(filepath)
            questions.extend(data["Question"].tolist())
            answers.extend(data["Answer"].tolist())
        else:
            print("Unsupported file format: ", file)

    # create a vector store for the questions
    print("create a vector store for the questions")
    question_store = InMemoryVectorStore(embedding=embeddings)
    question_store.add_texts(texts=questions)
    # dump the question store and the Q&A to files
    question_store.dump(f"{folder}/packaged_questions")
    with open(f"{folder}/Q&A.yaml", "w") as f:
        qa = {}
        qa["Questions"] = questions
        qa["Answers"] = answers
        yaml.dump(qa, f)

    # create a vector store for the data files
    print("create a vector store for the data files")
    vectorstore = InMemoryVectorStore(embedding=embeddings)
    for file in data_files:
        with open(f"{folder}/{file}", "r") as f:
            # recursive character text splitter is a good option when the source is just a long text file
            # it splits the text into chunks of a specified size with a specified overlap
            # text_splitter = RecursiveCharacterTextSplitter(
            #     chunk_size=300, chunk_overlap=50
            # )
            # splits = text_splitter.split_text(f.read())
            # data files that we use should be already formatted and separated by newlines
            splits = f.read().split("\n\n")
            vectorstore.add_texts(texts=splits)
    
    # dump the vector store to a file
    vectorstore.dump(f"{folder}/packaged_data")
    print("done!")
