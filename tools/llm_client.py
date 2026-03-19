from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    model="llama-3.1-8b-instant",     # Free, fast, no rate issues
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.7
)
