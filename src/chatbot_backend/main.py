from importlib.metadata import version
from fastapi import FastAPI

app = FastAPI(title='Chatbot Backend API', version=version('chatbot_backend'))


@app.get('/health', tags=['health'])
def health():
    return {"status":'ok', "version":version('chatbot_backend')}