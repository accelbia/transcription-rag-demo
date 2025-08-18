import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import run
from uvicorn.config import logger as uvicorn_logger  # Use uvicorn's logger
from fastapi.responses import HTMLResponse

# Use uvicorn's logger
logger = uvicorn_logger

prompt = ""

# Load environment variables from .env file
load_dotenv('./.env')
# Get the OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()
app.add_middleware(CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

@app.on_event("startup")
def on_startup():
    """
    Function to run on startup.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
    else:
        logger.info("OpenAI API key loaded successfully.")

# Check if the API key is set
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate


def get_transcript_text(video_id: str) -> str:
    """
    Fetch YouTube transcript for a video in English, with fallback for auto-generated captions.
    Works for both dict and object return types.
    """
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        # Try manual transcript first
        transcript = None
        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except Exception:
            # Fallback: auto-generated
            transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])

        transcript_data = transcript.fetch()

        # Join all snippet texts
        if transcript_data and hasattr(transcript_data[0], 'text'):
            transcript_text = " ".join(chunk.text for chunk in transcript_data)
        else:
            transcript_text = " ".join(chunk['text'] for chunk in transcript_data)

        return transcript_text

    except TranscriptsDisabled:
        logger.error("Captions are disabled for this video.")
    except NoTranscriptFound:
        logger.error("No transcript available in English.")
    except Exception as e:
        logger.error(f"Error fetching transcript: {e}")
    return ""

def build_retriever(video_id):
    transcript = get_transcript_text(video_id)
    if not transcript.strip():
        return None, None
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.create_documents([transcript])
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vector_store = FAISS.from_documents(chunks, embeddings)
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
    return retriever, transcript


# Format docs for context
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# ========== Prompt ==========
prompt = PromptTemplate(
    template="""
        You are a helpful assistant.
        Answer ONLY from the provided transcript context.
        If the context is insufficient, say you don't know.

        {context}
        Question: {question}
        """,
    input_variables=['context', 'question']
)


@app.get("/transcript/{video_id}")
def get_transcript(video_id: str):
    """
    Endpoint to fetch the transcript for a given YouTube video ID.
    """
    try:
        transcript_text = get_transcript_text(video_id)
        if not transcript_text:
            return {"error": "No transcript available."}
        return {"transcript": transcript_text}
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/")
def index():
    """
    Simple index page to test the API.
    """
    return HTMLResponse("""
    <html>
        <head>
            <title>YouTube Transcriber API</title>
        </head>
        <body>
            <h1>Welcome to the YouTube Transcriber API</h1>
            <p>Use the endpoint <code>/transcript/{video_id}</code> to fetch transcripts.</p>
        </body>
    </html>
    """)

from pydantic import BaseModel

class AskRequest(BaseModel):
    video_id: str
    question: str

@app.post("/ask")
def ask_question(request: AskRequest):
    logger.info(f"Received request: {request}")
    """
    Endpoint to ask a question about a YouTube video transcript.
    """
    try:
        retriever, transcript = build_retriever(request.video_id)
        if not retriever:
            return {"error": "No transcript available."}

        docs = retriever.invoke(request.question)
        context = format_docs(docs)

        if not context.strip():
            return {"answer": "I don't know."}

        llm = ChatOpenAI(model="gpt-3.5-turbo")
        answer = llm.invoke(prompt.format(context=context, question=request.question)).content

        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}