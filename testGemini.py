from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0
)

response = llm.invoke(
    "Tell me in one sentence why AI agents are useful."
)

print(response.content)

'''from dotenv import load_dotenv
import os

load_dotenv()

key = os.getenv("GOOGLE_API_KEY")

print("KEY FOUND:", key[:15])'''