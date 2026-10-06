from google import genai
from app.core.config import settings

client = genai.Client(api_key=settings.gemini_api_key)
reply = client.models.generate_content(model=settings.gemini_model, contents="Say hi in 5 words")
print(reply.text)