import os
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="models/gemini-3.6-flash",
    contents="Say hello in one sentence."
)

print(response.text)