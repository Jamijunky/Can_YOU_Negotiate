import os
import requests

url = "https://api.groq.com/openai/v1/models"
headers = {
    "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY')}",
    "Content-Type": "application/json"
}
response = requests.get(url, headers=headers)
print(response.json())
