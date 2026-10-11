# Python + FastAPI + OAuth2 Password Bearer + JWT Auth + RAG + Voyage AI Embeddings

A production-style **Retrieval-Augmented Generation (RAG) API** built with **FastAPI**.

This project combines **OAuth2 Password Bearer authentication**, **JWT access tokens**, **PostgreSQL + pgvector vector search**, **Voyage AI Embeddings**, and **Groq LLMs** to deliver context-aware answers from your own data.

The RAG pipeline returns source references **only when sufficiently relevant information is retrieved from PostgreSQL**. If no relevant database content is found, the LLM can answer normally without returning a source.

---

## 📌 Project Info

- **Last Updated:** 11-10-2026
- **Python Version:** 3.12

---

## 🖥️ Frontend Client

This repository contains the FastAPI backend for the RAG system.

A separate Vue 3 SPA frontend is available as a client application and provides:

- JWT authenticated user login
- RAG question interface
- AI-generated answer display
- Retrieved source document display
- Pinia state management
- Production-ready Vite build

The Vue frontend communicates with this API through the protected `/login-spa` and `/ask` endpoints.

Frontend repository:

- `vue-fastapi-jwt-auth-rag-three` - Vue 3 SPA client for interacting with this FastAPI RAG API

---

## ✨ Features

### 🔐 Authentication

- OAuth2 Password Bearer authentication
- JWT access tokens (HS256)
- Swagger UI OAuth2 authorization support
- Protected endpoints using Bearer tokens
- Separate login endpoint for SPA clients (`/login-spa`)
- Environment-based credentials

### 🧠 RAG Pipeline

- Ingests `.txt` documents from URLs
- Splits content into topic-based chunks
- Generates embeddings using Voyage AI Embeddings
- Stores vectors in PostgreSQL with pgvector
- Performs semantic vector retrieval
- Uses a relevance threshold to prevent unrelated documents from being used
- Returns source URLs only when relevant RAG content is retrieved
- Falls back to the LLM when no relevant RAG content is found

### 🤖 LLM Integration

- Groq API
- Model: `openai/gpt-oss-20b`
- Context-aware answer generation
- Structured prompting for retrieved RAG context
- Normal LLM responses when no relevant database context exists

### 🔎 Semantic Search

The retrieval pipeline uses:

- Query → embedding
- PostgreSQL + pgvector similarity search
- Cosine distance using `<->`
- Maximum of 3 retrieved chunks
- Relevance threshold of 0.45

Only documents with a cosine distance of `<= 0.45` are considered sufficiently relevant.

This prevents PostgreSQL from returning the closest available document simply because a query has no genuinely relevant match.

### 🗄️ Vector Database

PostgreSQL with pgvector stores:

- Document content
- Embeddings
- Source URL
- Embedding model
- Embedding version
- Timestamp

Optimizations include:

- `VECTOR(512)` column
- `ivfflat` index
- Normalized embeddings
- Cosine-distance based similarity search

### ⚙️ Background Processing

- FastAPI `BackgroundTasks`
- Background document ingestion
- Batched embedding generation
- Batched PostgreSQL inserts

### 🧪 Debug Tools

The `/debug/retrieve` endpoint can be used to inspect the RAG retrieval process without invoking the LLM.

It returns:

- Original query
- Number of retrieved documents
- Retrieved content
- Source URL
- Retrieval distance

---

## 📁 Project Structure

The application is organized into separate modules to improve maintainability while keeping the core RAG pipeline logic centralized.

Current structure:

- `app.py`
  - Creates the FastAPI application
  - Registers API routes
  - Handles application startup events

- `routes.py`
  - Contains all API endpoints
  - Handles authentication flows
  - Handles RAG queries
  - Handles document ingestion requests
  - Controls whether sources are returned

- `utils.py`
  - Contains the core RAG and service functionality
  - Hugging Face embedding generation
  - PostgreSQL + pgvector database operations
  - Document chunking and text processing
  - Document ingestion pipeline
  - Vector similarity retrieval
  - Retrieval relevance filtering
  - Groq LLM communication

- `auth.py`
  - Handles JWT authentication
  - Creates and validates access tokens
  - Provides authentication utilities for protected endpoints

- `models.py`
  - Contains Pydantic models
  - Defines request validation and API data schemas

- `config.py`
  - Contains application configuration
  - Loads environment-based values such as API keys, database configuration, and authentication parameters

This structure separates the API layer, authentication, configuration, data schemas, and RAG services while keeping the project simple and easy to extend.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login-spa` | Login endpoint for SPA clients (JWT) |
| POST | `/token` | OAuth2 Password Bearer token endpoint |
| POST | `/ask` | Ask questions using RAG and LLM 🔐 |
| POST | `/ingest` | Ingest `.txt` files from URLs 🔐 |
| POST | `/debug/retrieve` | Debug semantic retrieval 🔐 |

🔐 = Requires authentication

---

## ⚙️ Getting Started

### 1. Clone the Repository

    git clone https://github.com/your-username/your-repo.git
    cd your-repo

### 2. Create Virtual Environment

    python -m venv venv

Activate it on Windows PowerShell:

    venv\Scripts\activate

Activate it on Mac/Linux:

    source venv/bin/activate

### 3. Install Dependencies

    pip install -r requirements.txt

---

## ▶️ Run the Application

    uvicorn app:app --reload

Once running:

- API: `http://127.0.0.1:8000`
- Swagger Docs: `http://127.0.0.1:8000/docs`

### Using Swagger UI

1. Open `/docs`
2. Click **Authorize**
3. Sign in using your username and password through the OAuth2 Password flow
4. Swagger automatically stores and sends the Bearer token for protected endpoints

---

## 🔑 Authentication Flow

### Swagger / API Clients

1. Call `/token` using the OAuth2 Password flow
2. Receive a JWT access token
3. Use the token automatically through Swagger or manually with:

    Authorization: Bearer <your_token>

### SPA Clients

Frontend applications can authenticate via:

    POST /login-spa

The endpoint returns a JWT access token for subsequent authenticated requests.

---

## 🧠 How RAG Works

The current RAG flow is:

    User Query
        ↓
    Hugging Face Embedding
        ↓
    pgvector Similarity Search
        ↓
    Relevance Filtering
        ↓
    Groq LLM
        ↓
    Answer + Optional Sources

The retrieval stage uses:

- Maximum of 3 chunks
- Cosine distance using pgvector `<->`
- Relevance threshold of 0.45

The important distinction is that the system does not automatically consider the closest database result relevant.

If no retrieved document has a distance of `<= 0.45`, the database is considered to have no relevant information for the question.

The LLM then answers without RAG context and the API returns an empty `sources` array.

---

## 🔎 Retrieval Configuration

The retrieval function currently uses:

    def retrieve(query: str, k: int = 3, threshold: float = 0.45):

The PostgreSQL query:

1. Generates an embedding for the user question
2. Calculates vector distance against stored document embeddings
3. Filters results using the `0.45` threshold
4. Orders results by distance
5. Returns up to 3 relevant chunks

This prevents weak semantic matches from unnecessarily being passed to the LLM as RAG context.

### Why the threshold matters

Vector search will normally return the closest available documents, even when none are actually relevant.

For example, a question about France could still return documents about Vercel, MySQL, or Java because those documents are the closest available vectors.

The `0.45` threshold prevents those weak matches from being treated as relevant RAG context.

---

## 📚 Source Handling

Sources are returned based on actual successful RAG retrieval.

### Example: Source Triggered

Question:

    What is Java Spring Boot?

The database contains:

    Topic: Java Spring Boot is a Java framework for building MVC and APIs quickly and efficiently.

A retrieval distance around `0.30` is below the `0.45` threshold, so the document is accepted.

The API can return:

{
  "answer": "Java Spring Boot is a Java framework that simplifies the development of MVC applications and APIs. It provides convention‑over‑configuration, auto‑configuration, and embedded servers, allowing developers to build and deploy web services quickly and efficiently.",
  "sources": [
    "https://vanillajs.persteenolsen.com/rag-data-three.txt"
  ]
} 
  
The exact answer generated by the LLM may vary.

### Example: Source Not Triggered

Question:

    What is the capital of France?

No sufficiently relevant database document is found.

The LLM therefore answers normally without RAG context.

The API returns:

    {
      "answer": "The capital of France is Paris.",
      "sources": []
    }

Another example:

    Tell me a joke

If no relevant RAG document exists:

    {
      "answer": "Why did the...",
      "sources": []
    }

The exact LLM-generated answer will vary.

---

## 🧪 Debug Retrieval

The `/debug/retrieve` endpoint is useful for checking PostgreSQL retrieval without invoking the LLM.

Example request:

    What is Java Spring Boot?

Example response:

    {
  "query": "What is Java Spring Boot?",
  "count": 1,
  "results": [
    {
      "content": "Topic: Java Spring Boot Java Spring Boot is a Java framework for building MVC and APIs quickly and efficiently.",
      "source": "https://vanillajs.persteenolsen.com/rag-data-three.txt",
      "distance": 0.30772996406615305
    }
  ]
 }

Because `0.3077 <= 0.45`, the document is considered relevant.

For an unrelated question such as:

    Tell me a joke

The endpoint can return:

    {
      "query": "Tell me a joke",
      "count": 0,
      "results": []
    }

This means no sufficiently relevant document was found in PostgreSQL.

The endpoint is protected by JWT authentication.

---

## 📥 Document Ingestion

### `/ingest`

The ingestion endpoint:

1. Accepts a `.txt` file URL
2. Downloads and validates the document
3. Cleans the text
4. Splits the document into topic-based chunks
5. Generates embeddings using Voyage AI
6. Stores chunks and embeddings in PostgreSQL
7. Stores the original source URL
8. Processes the work as a FastAPI background task

The `/ingest` route itself was not changed when the retrieval threshold was introduced.

The threshold only affects retrieval after documents have already been ingested.

Changing the retrieval threshold does not require existing documents to be re-ingested.

---

## 🧾 Embeddings

- Model: `voyage-4-lite`
- 512-dimensional vectors
- Normalized embeddings
- Batch processing
- Retry support
- Voyage AI Embeddings API by MongoDB Atlas

The embedding model and version are stored with each document to support future embedding migrations.

---

## 🗄️ Database Initialization

Run the init database file by: python init_database.py

You may also have in mind that:

On application startup:

- Creates the `pgvector` extension
- Creates the `documents` table if it does not exist
- Creates the `ivfflat` vector index

The `documents` table contains:

- `id`
- `content`
- `embedding`
- `source`
- `embedding_model`
- `embedding_version`
- `created_at`

---

## 🛠️ Text Processing

The ingestion pipeline:

- Fetches `.txt` files from URLs
- Validates the HTTP response
- Validates the content type or `.txt` extension
- Removes empty lines
- Cleans text
- Splits documents whenever a line begins with `Topic:`

For example, a document containing multiple `Topic:` sections becomes multiple searchable chunks.

---

## 📊 Current Retrieval Configuration

| Setting | Current Value |
|---------|---------------|
| Embedding model | `voyage-4-lite` |
| Vector dimensions | 512 |
| Retrieval method | pgvector cosine distance |
| Maximum retrieved chunks | 3 |
| Relevance threshold | 0.45 |
| LLM | `openai/gpt-oss-20b` |
| Vector index | IVFFlat |

The `0.45` threshold is based on the current document collection and observed retrieval distances.

It may need to be adjusted as the knowledge base grows or the embedding strategy changes.

---

## 📌 Future Improvements

- 🔄 Refresh tokens
- 📊 Admin dashboard
- 🔍 Hybrid search (BM25 + vector)
- 📈 Monitoring and structured logging
- 🧩 Plugin/tool integrations
- 📚 Improved document management
- 🗑️ Document deletion and re-indexing
- 🔐 More granular authorization and user roles
- 🧠 Improved retrieval evaluation
- 🎯 Automatic relevance evaluation
- 📡 Streaming LLM responses

---

# 💡 Use Cases and Applications

This FastAPI RAG backend can be used as the foundation for AI-powered knowledge systems.

By combining document retrieval, vector search, relevance filtering, and LLM-generated responses, applications can provide answers grounded in trusted information sources while still allowing the LLM to answer general questions when the knowledge base has no relevant information.

## 💬 Chat Assistants

- Build AI-powered assistants connected to private knowledge sources
- Answer user questions using retrieved documents as context
- Provide source references when knowledge-base information is used
- Allow normal LLM responses when no relevant knowledge-base information exists

Examples:

- Customer support assistants
- Employee knowledge assistants
- Product support chatbots
- FAQ assistants

## 📚 Document Question Answering

- Query document collections using natural language
- Retrieve relevant information from documents
- Generate answers with source references
- Avoid presenting unrelated documents as supporting sources

Examples:

- Technical documentation assistants
- Policy and procedure assistants
- Research assistants
- Document analysis systems

## 🏢 Enterprise Knowledge Systems

- Connect employees with company knowledge bases
- Provide secure access to internal information
- Reduce time spent searching across multiple systems
- Return source references when internal knowledge is used

Examples:

- Internal company assistants
- HR knowledge systems
- IT support assistants
- Training platforms

## 🎓 Education and Learning Assistants

- Create AI tutors based on educational content
- Help users explore course material through questions
- Provide explanations grounded in learning resources

Examples:

- Course assistants
- Learning platforms
- Training systems
- Educational chatbots

## 🛠️ Developer and Technical Assistants

- Provide answers from technical documentation and repositories
- Help developers understand frameworks, APIs, and systems
- Improve access to technical knowledge
- Return relevant documentation sources

Examples:

- API documentation assistants
- Programming assistants
- DevOps assistants
- Software architecture assistants

## 🔎 Semantic Search and Knowledge Discovery

- Replace traditional keyword search with semantic search
- Find relevant information based on meaning rather than exact wording
- Filter weak vector matches using a relevance threshold
- Combine retrieval with natural language explanations

Examples:

- Enterprise search engines
- Research tools
- Digital libraries
- Knowledge management systems

## 🔐 Secure AI Applications

With FastAPI authentication, protected endpoints, and controlled access to knowledge sources, the backend can support secure AI applications.

Examples:

- Private company assistants
- Customer portals
- Role-based AI systems
- Member-only knowledge platforms

---

## 📄 License

MIT License

---

## 🙌 Final Notes

This project is designed as a **clean, production-style RAG backend** that can serve multiple clients.

The FastAPI API can be extended into:

- Chatbots
- Internal knowledge systems
- AI assistants
- Document search platforms
- Enterprise knowledge applications

The current implementation deliberately separates retrieval from answer generation.

When relevant information is found in PostgreSQL:

- The relevant chunks are passed to the LLM
- The LLM uses that context to answer the question
- The API returns the corresponding source URL

When no sufficiently relevant information is found:

- No RAG context is passed to the LLM
- The LLM can answer normally
- The API returns `sources: []`

This prevents unrelated database documents from being presented as sources simply because they happened to be the closest vector matches.

A Vue 3 SPA frontend is included as a separate client application, demonstrating how to securely integrate authentication, API communication, and RAG-based question answering into a modern web application.

Happy coding :-)
