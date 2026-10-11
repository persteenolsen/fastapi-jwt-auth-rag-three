from datetime import timedelta

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm

from auth import create_access_token, verify_token
from models import (
    LoginRequest,
    TokenResponse,
    PromptRequest,
    URLRequest,
)

from config import (
    FAKE_USERNAME,
    FAKE_PASSWORD,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

from utils import (
    retrieve,
    llm,
    fetch_txt_clean,
    chunk_txt,
    process_chunks,
)


router = APIRouter()


# -----------------------------
# LOGIN FOR VUE SPA
# -----------------------------
@router.post("/login-spa")
def login(form: OAuth2PasswordRequestForm = Depends()):
    if form.username != FAKE_USERNAME or form.password != FAKE_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(
        {"sub": form.username},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": token, "token_type": "bearer", "username": FAKE_USERNAME
    }

# -----------------------------
# OAUTH2 TOKEN FOR SWAGGER
# -----------------------------
@router.post("/token", response_model=TokenResponse)
def get_token(
    form: OAuth2PasswordRequestForm = Depends()
):

    if form.username != FAKE_USERNAME or form.password != FAKE_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(
        {"sub": form.username},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return TokenResponse(access_token=token)


# -----------------------------
# ROOT
# -----------------------------

@router.get("/")
def root():
    return {"status": "ok"}


# -----------------------------
# DEBUG RETRIEVAL
# -----------------------------
@router.post("/debug/retrieve")
def debug(
    req: PromptRequest,
    user=Depends(verify_token),
):
    docs = retrieve(req.prompt)

    return {
        "query": req.prompt,
        "count": len(docs),
        "results": docs,
    }


# -----------------------------
# ASK
# -----------------------------
@router.post("/ask")
def ask(
    req: PromptRequest,
    user=Depends(verify_token)
):

    docs = retrieve(req.prompt)

    print("\n=== RETRIEVAL DEBUG ===")
    print(f"Query: {req.prompt}\n")

    for i, d in enumerate(docs):
        print(f"[{i}] SOURCE: {d['source']}")
        print(f"DISTANCE: {d['distance']}")
        print(f"CONTENT: {d['content'][:200]}")
        print("------------------------")

    if docs:

        context = "\n\n".join(
            f"{d['content']} (source: {d['source']})"
            for d in docs
        )

        prompt = f"""
You are a helpful assistant.

Use the following context to answer the question when it is relevant.

Context:
{context}

Question:
{req.prompt}
"""

        answer = llm(prompt)

        sources = list(set(d["source"] for d in docs))

    else:

        # No relevant database information was found.
        prompt = req.prompt

        answer = llm(prompt)

        sources = []

    return {
        "answer": answer,
        "sources": sources,
    }


# -----------------------------
# INGEST
# -----------------------------

@router.post("/ingest")
def ingest(
    req: URLRequest,
    background_tasks: BackgroundTasks,
    user=Depends(verify_token),
):

    clean_text = fetch_txt_clean(req.url)

    chunks = chunk_txt(clean_text)

    background_tasks.add_task(
        process_chunks,
        chunks,
        req.url,
    )

    return {
        "message": "Processing started",
        "chunks": len(chunks),
    }
