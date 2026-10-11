"""
Utility functions for the RAG pipeline.

This module contains the core application services:

- PostgreSQL + pgvector database initialization
- Voyage AI embedding generation via MongoDB Atlas API
- Text cleaning and chunking
- Document ingestion
- Vector similarity retrieval
- Groq LLM communication
"""

# ============================================================
# IMPORTS
# ============================================================

import asyncio
import requests
import httpx
import numpy as np

from sqlalchemy import create_engine, text
from groq import Groq
from fastapi import HTTPException

from config import (
    DATABASE_URL,
    GROQ_API_KEY,
    VOYAGE_API_KEY,
)

# ============================================================
# CLIENTS AND CONFIGURATION
# ============================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

client = Groq(api_key=GROQ_API_KEY)

# MongoDB Atlas Voyage AI Embeddings API
VOYAGE_URL = "https://ai.mongodb.com/v1/embeddings"

EMBED_MODEL = "voyage-4-lite"
EMBED_DIMENSION = 512

# Increment when the embedding strategy changes.
EMBED_VERSION = 4


# ============================================================
# EMBEDDINGS
# ============================================================

def normalize(vec):
    """
    Normalize an embedding vector for cosine similarity.
    """

    vector = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(vector)

    if norm == 0:
        raise ValueError("Embedding vector has zero magnitude")

    return (vector / norm).tolist()


async def voyage_embed(
    texts: list[str],
    input_type: str = "document",
):
    """
    Generate embeddings using the MongoDB Atlas Voyage API.

    input_type:
        document = stored document chunks
        query    = user search queries
    """

    if not texts:
        return []

    if input_type not in ("document", "query"):
        raise ValueError("Invalid Voyage input_type")

    async with httpx.AsyncClient(timeout=60.0) as http_client:

        response = await http_client.post(
            VOYAGE_URL,
            headers={
                "Authorization": f"Bearer {VOYAGE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "input": texts,
                "model": EMBED_MODEL,
                "input_type": input_type,
                "output_dimension": EMBED_DIMENSION,
            },
        )

        if response.status_code != 200:
            print("VOYAGE STATUS:", response.status_code)
            print("VOYAGE RESPONSE:", response.text)

        response.raise_for_status()

        result = response.json()

    # Preserve the original input order.
    items = sorted(
        result["data"],
        key=lambda item: item["index"],
    )

    vectors = [
        item["embedding"]
        for item in items
    ]

    if len(vectors) != len(texts):
        raise ValueError(
            "Voyage returned an unexpected number of embeddings"
        )

    if any(
        len(vector) != EMBED_DIMENSION
        for vector in vectors
    ):
        raise ValueError(
            f"Expected {EMBED_DIMENSION}-dimensional embeddings"
        )

    return [
        normalize(vector)
        for vector in vectors
    ]


def embed_batch(
    texts: list[str],
    input_type: str = "document",
):
    """
    Synchronous wrapper around the asynchronous Voyage API call.

    Includes a small retry mechanism for temporary failures.
    """

    for attempt in range(3):

        try:
            return asyncio.run(
                voyage_embed(texts, input_type)
            )

        except Exception:
            if attempt == 2:
                raise


# ============================================================
# DATABASE
# ============================================================

def init_db():
    """
    Initialize PostgreSQL objects required by the RAG system.

    NOTE:
    CREATE TABLE IF NOT EXISTS does not change an existing
    VECTOR(384) column to VECTOR(512).
    Migrate an existing database separately.
    """

    with engine.begin() as conn:

        conn.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector;")
        )

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                content TEXT,
                embedding VECTOR(512),
                source TEXT,
                embedding_model TEXT,
                embedding_version INT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS documents_embedding_idx
            ON documents
            USING ivfflat
            (embedding vector_cosine_ops)
            WITH (lists = 100);
        """))


# ============================================================
# DOCUMENT PROCESSING
# ============================================================

def chunk_txt(text_value: str):
    """
    Split text into chunks whenever a line begins with 'Topic:'.
    """

    chunks = []
    current_chunk = []

    for line in text_value.splitlines():

        line = line.strip()

        if line.startswith("Topic:"):

            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []

        if line:
            current_chunk.append(line)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def fetch_txt_clean(url: str):
    """
    Download and clean a plain text document.
    """

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Request failed",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail="Failed to fetch URL",
        )

    content_type = response.headers.get("Content-Type", "")

    if not (
        "text/plain" in content_type
        or url.endswith(".txt")
    ):
        raise HTTPException(
            status_code=400,
            detail="URL must be .txt",
        )

    lines = [
        line.strip()
        for line in response.text.splitlines()
        if line.strip()
    ]

    return "\n".join(lines)


# ============================================================
# INGESTION WORKER
# ============================================================

def process_chunks(chunks: list[str], source: str):
    """
    Generate Voyage embeddings and store document chunks.

    Normally executed as a FastAPI BackgroundTask.
    """

    batch_size = 32

    with engine.begin() as conn:

        for index in range(0, len(chunks), batch_size):

            batch = chunks[index:index + batch_size]

            vectors = embed_batch(
                batch,
                input_type="document",
            )

            for chunk, vector in zip(batch, vectors):

                conn.execute(
                    text("""
                        INSERT INTO documents
                        (
                            content,
                            embedding,
                            source,
                            embedding_model,
                            embedding_version
                        )
                        VALUES
                        (
                            :content,
                            CAST(:embedding AS vector),
                            :source,
                            :model,
                            :version
                        )
                    """),
                    {
                        "content": chunk,
                        "embedding": vector,
                        "source": source,
                        "model": EMBED_MODEL,
                        "version": EMBED_VERSION,
                    },
                )


# ============================================================
# RETRIEVAL
# ============================================================

def retrieve(
    query: str,
    k: int = 3,
    threshold: float = 0.45,
):
    """
    Retrieve document chunks using cosine distance.

    Lower distance means a more similar vector.
    """

    query_vector = embed_batch(
        [query],
        input_type="query",
    )[0]

    with engine.begin() as conn:

        rows = conn.execute(
            text("""
                SELECT
                    content,
                    source,
                    embedding <=> CAST(:embedding AS vector)
                        AS distance
                FROM documents
                WHERE embedding IS NOT NULL
                  AND embedding_model = :model
                  AND embedding_version = :version
                  AND embedding <=> CAST(:embedding AS vector)
                      <= :threshold
                ORDER BY distance
                LIMIT :k
            """),
            {
                "embedding": query_vector,
                "k": k,
                "threshold": threshold,
                "model": EMBED_MODEL,
                "version": EMBED_VERSION,
            },
        ).fetchall()

    return [
        {
            "content": row[0],
            "source": row[1],
            "distance": float(row[2]),
        }
        for row in rows
    ]


# ============================================================
# LARGE LANGUAGE MODEL
# ============================================================

def llm(prompt: str):
    """
    Send the final RAG prompt to Groq and return the answer.
    """

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.7,
        max_tokens=800,
    )

    return response.choices[0].message.content