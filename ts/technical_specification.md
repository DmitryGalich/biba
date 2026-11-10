# Technical Specification (TS) for Private RAG System Development

## 1. General Information

### 1.1. System Name
System Name: **Local On-Premise Information Retrieval RAG System (Retrieval-Augmented Generation)**.

### 1.2. Project Goal
Development of a fully isolated, secure, and fault-tolerant software system for annotating, indexing, and intelligently searching local documents using Large Language Models (LLMs) on self-hosted hardware (On-Premise).

### 1.3. Key Objectives
* Isolate corporate data from external cloud providers.
* Enforce granular user access control to documents and chats via OAuth2/OIDC.
* Ensure high-speed response generation and context retrieval leveraging GPU acceleration (NVIDIA CUDA).

## 2. Architecture and Technology Stack

The system is built on a microservices architecture deployed via Docker Compose.

### 2.1. Technology Stack
* **Reverse Proxy (API Gateway):** Nginx 1.27.
* **Authentication & Authorization:** Keycloak 26.3 + PostgreSQL 16 (as Keycloak metadata database).
* **Backend Orchestrator:** Rust (recommended web frameworks: `Axum` or `Actix-web`).
* **Vector Database:** Qdrant (latest stable release).
* **LLM Runtime Environment:** Ollama Docker with NVIDIA Container Toolkit (CUDA) support.

## 3. Functional Requirements

The system is divided into 3 core functional submodules.

### 3.1. Identity and Access Management (IAM) Subsystem
* **System Authentication:** Users gain access to the API/UI only after successful authorization via Keycloak.
* **Token Management:** The client transmits the token in the `Authorization: Bearer <JWT>` header.
* **Backend Validation:** The backend (Rust) must validate incoming JWT tokens on the fly (signature, expiration) utilizing open keys from Keycloak (`JWKS`).
* **Role-Based Access Control (RBAC):** Users must be divided into at least two roles:
  * `User`: Can chat, create custom dialogue sessions, and read documents they have explicit access to.
  * `Admin`: Can upload new documents, delete files, and view system metrics.

### 3.2. Document Indexing Subsystem (Data Ingestion Pipeline)
* **Supported File Formats:** `.txt`, `.pdf`, `.docx`, and `.md`.
* **Data Ingestion Pipeline:**
  1. Extract raw text from the uploaded file.
  2. Sanitize text by removing junk characters and format noise.
  3. **Text Splitting (Chunking):** Split text into semantic fragments (chunks) of up to 500-1000 tokens/characters with a 10-20% overlap to preserve context at fragment boundaries.
  4. **Embedding Generation:** Send each chunk to Ollama to generate vector embeddings (recommended models: `nomic-embed-text` or `bge-m3`).
  5. **Vector Storage:** Insert the generated vector, original chunk text, and metadata (filename, document ID, creator ID) into the Qdrant database.

### 3.3. Chat and Response Generation Subsystem (RAG Pipeline)
* **Dialogue Session Management:** Ability to create, rename, and delete chat sessions (message history persists in a database).
* **Context Retrieval:**
  1. Upon receiving a new user prompt, the backend vectorizes it via Ollama's embedding model.
  2. The backend performs a Cosine Similarity nearest-neighbor search in Qdrant, requesting the `Top-K` (e.g., 3-5) most relevant text chunks.
* **Response Generation:**
  1. Construct an augmented prompt (System Prompt + Context from Qdrant + Chat History + User Prompt).
  2. Dispatch the prompt to Ollama's generative model (recommended: `llama3.1:8b`, `mistral:7b`, or `qwen2.5:7b`).
  3. **Token Streaming:** The response from Ollama must stream to the user in real time using **Server-Sent Events (SSE)** or WebSockets via the Rust backend.

## 4. REST API Specification (Target Endpoints)

All endpoints, except `/api/v1/health`, require an `Authorization: Bearer <JWT>` header.

### 4.1. General
* `GET /api/v1/health` — Backend health check (verifies connections to Ollama, Qdrant, and DB).

### 4.2. Document Management (Admin Access Only)
* `POST /api/v1/documents/upload` — File upload (`multipart/form-data`). Returns document ID and processing queue status.
* `GET /api/v1/documents` — Fetch a list of all indexed documents.
* `DELETE /api/v1/documents/{id}` — Delete a document from the system and purge corresponding vector points from Qdrant.

### 4.3. Chat and RAG Management (User / Admin Access)
* `POST /api/v1/chats` — Initialize a new dialogue session.
* `GET /api/v1/chats` — Fetch a list of chat sessions belonging to the current user.
* `GET /api/v1/chats/{id}/history` — Load message history for a specific chat.
* `POST /api/v1/chats/{id}/message` — Submit a new query.
  * *Parameters:* `stream: true/false`.
  * *Response:* Standard JSON payload or text stream (`text/event-stream`).

## 5. Non-Functional Requirements

### 5.1. Security and Data Isolation
* **Network Isolation:** All services, except `gateway`, must reside within an isolated docker network (`internal_network`) and must not expose ports to the host machine.
* **Input Validation:** Mitigate Prompt Injection attacks by sanitizing and separating user queries from the injected context block in system instructions.
* **Data Sanitization:** When a user or document is deleted, the data must be completely erased from Qdrant vector spaces.

### 5.2. Performance and Scalability
* **Asynchronous Design:** The Rust backend must leverage non-blocking I/O (`tokio`) to efficiently manage hundreds of concurrent SSE connections.
* **Latency Limits:** Vector search latency in Qdrant must remain below 100 ms. Time to First Token (TTFT) from Ollama must not exceed 2 seconds on GPU-accelerated hardware.
* **Task Queues:** File ingestion must be handled via a background queue (e.g., using `tokio::sync::mpsc`) so that large file uploads do not block chat generation requests.

### 5.3. Fault Tolerance
* Automatic container recovery on failure (`restart: unless-stopped`).
* Isolated logging configurations for Nginx, Keycloak, and the Rust backend, mapped to host directories for persistence.

## 6. Acceptance Criteria
1. The full application stack boots successfully with a single command: `docker-compose up -d`.
2. Unauthorized requests to `/api/` are rejected with a `401 Unauthorized` status code by Nginx or the Rust backend.
3. Uploaded documents are properly chunked, indexed, and leveraged by the LLM to answer contextual user queries.
4. Response token generation utilizes real-time streaming (SSE) instead of waiting for full generation cycles.