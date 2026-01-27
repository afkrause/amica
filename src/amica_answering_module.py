"""
Answer generation module that uses ollama and langchain to generate answers based on a chat history and its knowledgebase.
This module is designed to run in a separate thread and communicate with the main application via multiprocessing queues.

The module also includes a script to run the thread on a separate machine and communicate via a manager server.
"""


import time
from typing import Iterator

import yaml

import ollama
from ollama import ChatResponse

from langchain_core.vectorstores import VectorStoreRetriever, InMemoryVectorStore
from langchain_huggingface.embeddings.huggingface import HuggingFaceEmbeddings

import multiprocessing
from multiprocessing import Process, Queue
from multiprocessing.managers import BaseManager

# dictionary with functions that can be called by the Q&A
from dynamic_answers import qa_functions

class ChatHistory:
    """A class to manage the chat history and keep it within a maximum length."""

    def __init__(self, max_length=10):
        #: messages are stored as a list of dictionaries with "role" and "content" keys.
        #: "role" can be "user" or "assistant", "content" is the message text.
        # workaround when first query ignored system prompt
        # self.messages = [{"role": "user", "content": "Hallo Amica!"},
        #                  {"role": "assistant", "content": "Hallo! Wie kann ich dir helfen?"}]
        # self.length = 2
        self.messages = []
        self.length = 0
        self.max_length = max_length

    def addHuman(self, message: str):
        """Add a user message to the chat history."""

        #: add a new message to the chat history
        self.messages.append({"role": "user", "content": message})
        self.length += 1
        #: trunkate the chat history if it exceeds the maximum length or it starts with an AI response
        #: we want to keep the chat history starting with a user message
        if self.length > self.max_length:
            while self.length > self.max_length or self.messages[0]["role"] != "user":
                self.messages.pop(0)
                self.length -= 1

    def addAI(self, message: str):
        """Add an AI response to the chat history."""

        #: add a new message to the chat history
        self.messages.append({"role": "assistant", "content": message})
        self.length += 1
        #: trunkate the chat history if it exceeds the maximum length or it starts with an AI response
        #: we want to keep the chat history starting with a user message
        if self.length > self.max_length:
            while self.length > self.max_length or self.messages[0]["role"] != "user":
                self.messages.pop(0)
                self.length -= 1

    def clear(self):
        """Clear the chat history."""

        # self.messages = [{"role": "user", "content": "Hallo Amica!"},
        #                  {"role": "assistant", "content": "Hallo! Wie kann ich dir helfen?"}]
        # self.length = 2
        self.messages = []
        self.length = 0



def answer_generation_thread(queues: tuple[Queue, Queue, Queue], assets: dict, model_parameters: dict):
    """Thread to handle the answer generation process using ollama and langchain. This function listens for queries, processes them, and generates answers using the provided model parameters.
    
    Args:
        queues: A tuple containing the query queue, answer queue, and log queue.
        assets: A tuple containing the folder path, list of QA files, list of data files, and prompt file
        model_parameters: A tuple containing the language tag, main llama version, tool llama version, embedding model, and semantic threshold.
    """

    global language

    query_queue, answer_queue, log_queue = queues

    folder = assets["folder"]
    qa_file = assets["qa_file"]
    packaged_questions = assets["qa_data"]
    packaged_data = assets["llm_data"]
    prompt_file = assets["prompt_file"]

    language = model_parameters["language"]
    main_llama_version = model_parameters["main_llama_version"]
    tool_llama_version = model_parameters["tool_llama_version"]
    embeddings_model = model_parameters["embeddings_model"]
    semantic_threshold = model_parameters["semantic_threshold"]
    enable_rephrasing = model_parameters["enable_rephrasing"]

    print("Starting answer generation process...")

    def search_qa(question: str) -> tuple[str, float]:
        """
        Search for the question in the question store.

        Args:
            question: The question to search for.
        Returns:
            A tuple containing the best match question and its score.
        """

        start = time.time()
        matched_question, score = question_store.similarity_search_with_score(question, 1)[0]

        matched_question = matched_question.page_content    # get the text of the question from the Document object
        log_queue.put((start, time.time(), "semantic search", (matched_question, score,)))

        return matched_question, score

    def reply_from_qa(question: str, chat: ChatHistory):
        """Reply to the question using the predefined answers from the QA files.

        Args:
            question: The question from the Q&A.
            chat: The chat history to which the answer will be added.
        """

        # find where the question is in the questions list
        # answer is at the same index in the answers list
        answer = answers[questions.index(question)]

        # check if the answer starts with @, which means it is a function call from qa_functions
        # if it is, calls the function and reassigns the answer
        if answer[0] == "@":
            try:
                answer = qa_functions[answer](language)
            except KeyError:
                #: in the case the function is not found in qa_functions, we just return a default answer
                #: this can happen if the function is not implemented or the name is misspelled
                print(f"Function {answer} not found in qa_functions, using the original answer.")
                if language == "de":
                    answer = "Entschuldigung, ich kenne die Antwort auf diese Frage nicht."
                else:
                    answer = "Sorry, I don't know the answer to that question."
        # sends the answer in the answer_queue + a marker for the end of the answer
        answer_queue.put(answer)
        answer_queue.put("<<end of answer>>")
        # saves the answer to the chat history
        chat.addAI(answer)

    def rephrase_and_search_qa(chat: ChatHistory) -> tuple[str, float, str]:
        """
        Rephrase the question based on the chat history and search for it in the question store.

        Args:
            chat: The chat history containing the messages.
        Returns:
            A tuple containing the best match and its score, as well as the rephrased question."""

        # check if the chat history has enough messages to rephrase the question
        if len(chat.messages) > 2:
            start = time.time()
            contextualized_question = rephrase_question(chat_history)
            log_queue.put((start, time.time(), "question rephrased", (contextualized_question,)))
        else:
            # if there is not enough context in the chat history, use the original question
            contextualized_question = chat_history.messages[-1]["content"]

        start = time.time()
        # search for the rephrased question in the question store
        question, score = question_store.similarity_search_with_score(contextualized_question, 1)[0]
        question = question.page_content    # get the text of the question from the Document object

        log_queue.put((start, time.time(), "semantic search", (question, score)))
        # return the question, the score, and the rephrased question
        return question, score, contextualized_question

    def rephrase_question(chat: ChatHistory) -> str:
        """
        Rephrase the last question based on the chat history.

        Args:
            chat: The chat history containing the messages.
        Returns:
            The rephrased question as a string.
        """

        messages = chat.messages

        # prompt = f"""You are a system that rephrases user questions. Look at the previous interactions and the latest user question. If there are pronouns ('it', 'that', 'there', 'here', 'so', etc) in the question, replace them with the things they refer to. DON'T change any nouns or verbs in the question. Don't change the pronouns that refer to you. Don't add any comments, just give me the question. You MUST reply with just the question in German. DON'T ANSWER THE QUESTION ITSELF.
        #               previous messages:
        #               user: {messages[-3]["content"]}
        #               assistant: {messages[-2]["content"]}
        #               latest query by user: {messages[-1]["content"]}"""

        prompt = f"""Given the last 3 messages of a conversation between a user and an AI assistant, rephrase the latest user question to be more specific. Ensure that the rephrased question is clear and unambiguous and can be fully understood without ever knowing the previous messages or who is asking it. Include as much information as possible, especially names or any other identifiable information. Do not invent anz yourself, only use information given to you. Do not add any comments. Respond only with the rephrased question in {language}. Do not answer the question itself.
                It is currently {get_datetime()}.
                Previous messages:
                user: {messages[-3]["content"]}
                assistant: {messages[-2]["content"]}
                user: {messages[-1]["content"]}"""

        return ollama.generate(tool_llama_version, prompt=prompt, keep_alive=-1, stream=False, think=False,
                                   options={"temperature": 0.5, "repeat_penalty": 0.8}
                               )["response"]

    def get_datetime() -> str:
        """Get the current date, weekday and time formatted as a string."""
        return time.strftime("%d.%m.%Y") + " " + time.strftime("%A") + " " + time.strftime("%H:%M")

    def start_answer_stream(chat: ChatHistory, context_query: str) -> Iterator[ChatResponse]:
        """
        Start the answer stream with chat history and context retrieved based on the context query.

        Args:
            chat: The chat history containing the messages.
            context_query: The query to retrieve relevant context from the vector store.
        Returns:
            An iterator that yields ChatResponse objects containing the generated answer.
        """

        start = time.time()
        # retrieve context based on the context query
        context = vectorstore.similarity_search_with_score(context_query, k=4)
        # context is a list of tuples (Document, score)
        # where Document has a page_content attribute which is the text of the "document" in out case a context
        # we take the first element of the list and get its page_content
        context = [c[0].page_content for c in context]
        print(context)
        log_queue.put((start, time.time(), "history_aware_retriever", (context,)))
        messages = [{"role": "system", "content": system_prompt.format(context=context,
                                                                       date_time=get_datetime())}]
        messages.extend(chat.messages)

        return ollama.chat(main_llama_version, messages=messages, keep_alive=-1, stream=True, think=False,)

    def reply_with_AI(chat: ChatHistory, context_query: str):
        """
        Reply to the question using AI with the chat history and context retrieved based on the context query.

        Args:
            chat: The chat history containing the messages.
            context_query: The query to retrieve relevant context from the vector store.
        """

        # ollama generates a response in chunks, so we want to accumulate them
        # we want to split the answer into sentences and send full sentences instead of chunks
        # we also want to keep track of the full answer to save it to the chat history
        start = time.time()
        sentence = ""               # accumulates the current sentence
        full_answer = ""            # accumulates the full answer

        response = start_answer_stream(chat, context_query) # start the answer stream with chat history and context
        for raw_chunk in response:
            # retrieve the text from the chunk from ollama response
            chunk = raw_chunk.message.content
            sentence += chunk
            if len(chunk) > 0:
                # check if the chunk ends with a sentence ending punctuation or a newline
                # if it does, we consider it a complete sentence and send it to the answer_queue
                # we also check if the sentence ends with a period, and it's not a short form like "Dr.", "Mr.", "Mrs.", "Ms.", "Prof."
                if (chunk[-1] in ["?", "!"] or
                        (chunk[-1] == "." and not any(
                            sentence.endswith(short) for short in ["Dr.", "Mr.", "Mrs.", "Ms.", "Prof."]))
                        or "\n" in sentence):
                    # send the sentence to the answer_queue
                    answer_queue.put(sentence)
                    # accumulate the sentences into a full answer
                    full_answer += sentence
                    log_queue.put((start, time.time(), "sentence generated", (sentence,)))
                    sentence = ""
                    start = time.time()
        # after the loop, we check if there is any part of the answer left that is not sent yet
        if len(sentence) > 0:
            answer_queue.put(sentence)
            full_answer += sentence
            log_queue.put((start, time.time(), "sentence generated", (sentence,)))
        # finally, we send a marker for the end of the answer
        answer_queue.put("<<end of answer>>")
        chat.addAI(full_answer)


    # load the embeddings model
    embeddings = HuggingFaceEmbeddings(model_name=embeddings_model,
                                        model_kwargs = {'device': 'cpu'}
                                       )

    try:
        with open(f"{folder}/{qa_file}", "r") as f:
            qa_data = yaml.safe_load(f)
            answers = qa_data["Answers"]
            questions = qa_data["Questions"]
            print("Loaded questions and answers from the Q&A file")
    except FileNotFoundError:
        print(f"Q&A file not found, exiting")
        exit(1)

    try:
        question_store = InMemoryVectorStore.load(f"{folder}/{packaged_questions}", embedding=embeddings)
        print("Loaded question store")
    except FileNotFoundError:
        print("Question store not found, exiting")

    try:
        vectorstore = InMemoryVectorStore.load(f"{folder}/{packaged_data}", embedding=embeddings)
        print("Loaded vector store")
    except FileNotFoundError:
        print("Vector store not found, exiting")
        exit(1)    # # load the questions and answers from the qa files

    system_prompt = open(f"{folder}/{prompt_file}", "r").read()
    chat_history = ChatHistory()

    # Sending a None prompt to ollama loads the model without generating any text
    # keep alive is set to -1 to keep the model loaded indefinitely
    ollama.generate(main_llama_version, prompt=None, keep_alive=-1, stream=False)
    ollama.generate(tool_llama_version, prompt=None, keep_alive=-1, stream=False)


    # main loop to handle incoming queries
    while True:
        # wait for a query to be added to the query queue
        if query_queue.empty():
            # sleep for a short time to avoid busy waiting
            time.sleep(0.1)
        else:
            query = query_queue.get()
            # special commands to control the answering process
            if query == "<<hlt>>":
                # halt the answering process
                print("Stopping ollama...")
                # sending a None prompt to ollama doesn't generate any text, specifying keep_alive=0 unloads the model immediately
                ollama.generate(main_llama_version, prompt=None, keep_alive=0, stream=False)
                ollama.generate(tool_llama_version, prompt=None, keep_alive=0, stream=False)
                break
            elif query == "<<clr>>":
                # clear the chat history
                chat_history.clear()
                continue

            print("received query: ", query)

            # add the query to the chat history
            chat_history.addHuman(query)
            # run semantic matching on the question
            hit, score = search_qa(query)

            # if the score is above the threshold, answer the question with a predefined answer
            if score > semantic_threshold:
                print("Semantic search hit: ", hit, " with score: ", score)
                reply_from_qa(hit, chat_history)

            # if the score is below the threshold and there is enough context in the chat history, rephrase the question and search again
            elif len(chat_history.messages) > 2 and enable_rephrasing:
                hit, score, contextualized_query = rephrase_and_search_qa(chat_history)
                print("Contextualized query: ", contextualized_query)
                if score > semantic_threshold:
                    print("Rephrased search hit: ", hit, " with score: ", score)
                    reply_from_qa(hit, chat_history)
                else:
                    # if the score is still below the threshold use AI to answer the question
                    # contextualized query is used to search for relevant context
                    reply_with_AI(chat_history, contextualized_query)
            else:
                # if there is not enough context in the chat history, use AI to answer the question directly
                reply_with_AI(chat_history, query)


if __name__ == "__main__":
    # This script is here if the answering module is run as a standalone program for example on a separate machine.

    # set start method to spawn to allow CUDA to work with multiprocessing
    multiprocessing.set_start_method('spawn')

    config_file = "config.yaml"

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

    # create queues for communication between the processes
    query_queue = Queue()
    answer_queue = Queue()
    log_queue = Queue()

    # pack the queues into a tuple for easier passing to the process
    queues = (query_queue, answer_queue, log_queue)

    # start the answer generation process in a separate process
    answer_process = Process(target=answer_generation_thread, args=(queues, assets, model_parameters))
    answer_process.start()

    # create a manager to handle the queues and allow remote access
    class QueueManager(BaseManager): pass
    QueueManager.register('get_query_queue', callable=lambda: query_queue)
    QueueManager.register('get_answer_queue', callable=lambda: answer_queue)
    QueueManager.register('get_log_queue', callable=lambda: log_queue)

    # start the manager server on localhost at port 5000
    m = QueueManager(address=('', 5000), authkey=b'abracadabra')
    s = m.get_server()
    s.serve_forever()
