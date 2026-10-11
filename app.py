from fastapi import FastAPI

from routes import router
from utils import init_db


# 06-05-2026 - For allowing a Vue frontend in another domain
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Python + FastApi + JWT Auth + RAG Pipeline + Voyage AI embeddings",
    description="11-10-2026 - FastAPI with JWT Auth serving an RAG Application powered by Groq + Voyage AI embeddings",
    version="0.0.2",
    contact={
        "name": "Per Olsen",
        "url": "https://persteenolsen.netlify.app",
    },
)


# 21-07-2026 - For allowing a Vue frontend in another domain
# Set up CORS middleware
origins = [

    # Not sure if this is needed, but adding just in case
    "https://fastapi-jwt-auth-rag-three.vercel.app",

    # The domain name of the Vue 3 SPA Client
    "https://vue.fastapi.jwt.auth.rag.three.persteenolsen.com",
     
    # Allow my local Vue SPA
    "http://localhost:3000"
    
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)


@app.on_event("startup")
def startup():
    init_db()
