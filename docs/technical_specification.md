# Technical Specification (TS) for Private RAG System Development

## 1. General Information

### 1.1. System Name
**Local On-Premise Information Retrieval RAG System (Retrieval-Augmented Generation)**

### 1.2. Project Goal
Development of a fully isolated, high-performance, and fault-tolerant software system for indexing and intelligently searching local documents using Large Language Models (LLMs) on consumer-grade self-hosted hardware (NVIDIA RTX 3060, 6 GB VRAM).

### 1.3. Key Objectives
* Completely isolate data processing from external cloud providers.
* Maximize hardware efficiency to fit both Embedding and Generative models strictly within a **6 GB VRAM budget** without CPU offloading.
* Ensure low-latency response generation and context retrieval leveraging GPU acceleration (NVIDIA CUDA), gRPC, and real-time token streaming.

---

## 2. Architecture and Technology Stack

The system is built on a microservices architecture deployed via Docker Compose within an isolated internal network.

### 2.1. Technology Stack
* **Reverse Proxy (API Gateway):** Nginx 1.27 (configured with disabled proxy buffering for Server-Sent Events).
* **Backend Orchestrator:** Rust (`Axum` web framework, `Tokio` async runtime).
* **Relational Database:** PostgreSQL 16 + `sqlx` (for storing chat sessions, message history, and document processing statuses).
* **Vector Database:** Qdrant (latest stable release) using **gRPC** protocol (`qdrant-client`) and **Int8 Scalar Quantization**.
* **LLM Runtime Environment:** Ollama Docker with NVIDIA Container Toolkit (CUDA), **Flash Attention**, and **8-bit KV-Cache quantization**.

---

## 3. Hardware & Performance Optimization Requirements

To prevent Out-Of-Memory (OOM) errors and ensure high inference speed on a 6 GB GPU:

1. **Model Quantization:** Use 4-bit GGUF quantized models (`Q4_K_M` format) to reduce VRAM footprint by ~70% with negligible quality loss.
2. **KV-Cache & Attention Optimization:** Enable `OLLAMA_FLASH_ATTENTION=1` and `OLLAMA_KV_CACHE_TYPE=q8_0` in Ollama to save up to 1.5 GB of VRAM during long-context processing.
3. **Context Window Cap:** Strictly limit the LLM context window to `num_ctx: 4096` tokens per request.
4. **Vector Quantization:** Enable `ScalarQuantization (Int8)` in Qdrant collections to reduce RAM usage by 4x and accelerate vector similarity search.
5. **Batched Inference:** Process document chunk embeddings in batches (e.g., 32 chunks per HTTP request) rather than sequential single-chunk requests.

---

## 4. Functional Requirements

The system is divided into 2 core functional submodules (no authentication layer required).

### 4.1. Document Indexing Subsystem (Data Ingestion Pipeline)
* **Supported File Formats:** `.txt`, `.md`, `.pdf`, and `.docx`.
* **Asynchronous Background Queue:** File uploads must immediately return a `202 Accepted` status with a `document_id`, pushing the heavy parsing/embedding workload into an internal `tokio::sync::mpsc` worker queue.
* **Data Ingestion Pipeline:**
  1. Extract raw text from the uploaded file (`pdf-extract` for PDF, `zip` + `quick-xml` for DOCX).
  2. Sanitize text by removing junk characters and excessive whitespace.
  3. **Semantic Chunking:** Split text using `text-splitter` (`MarkdownSplitter` / `TextSplitter`) into fragments of up to **600 characters** with a **100-character overlap** (~15%) to preserve context across boundaries.
  4. **Batched Embedding Generation:** Send chunks in batches to Ollama using the lightweight **`nomic-embed-text`** model (~270 MB VRAM, 768 dimensions).
  5. **Vector Storage:** Upsert vectors, original chunk text, and metadata (`document_id`, `filename`, `chunk_index`) into Qdrant via gRPC, then update the document status to `ready` in PostgreSQL.

### 4.2. Chat and Response Generation Subsystem (RAG Pipeline)
* **Dialogue Session Management:** Create, list, rename, and delete chat sessions. All user prompts and assistant responses are persisted in PostgreSQL.
* **Context Retrieval:**
  1. Vectorize the incoming user query via Ollama (`nomic-embed-text`).
  2. Perform a Cosine Similarity search in Qdrant via gRPC, requesting `Top-K` (default: 4) chunks with a minimum similarity threshold (`score_threshold >= 0.65`) to filter out irrelevant noise.
  3. *Fallback:* If no chunks pass the threshold, return a predefined message stating that the answer is not found in the knowledge base without invoking the LLM.
* **Response Generation:**
  1. Construct an augmented prompt: `System Prompt (strict grounding rules) + Retrieved Context + Recent Chat History + User Query`.
  2. Dispatch the prompt to Ollama's generative model (**`qwen2.5:7b-instruct-q4_K_M`**, ~4.7 GB VRAM) with `temperature: 0.1` and `num_ctx: 4096`.
  3. **Token Streaming:** Stream generated tokens in real time to the client via **Server-Sent Events (`text/event-stream`)** through Rust/Axum and Nginx.

---

## 5. REST API Specification (Target Endpoints)

All endpoints are open within the local network (no `Authorization` headers required).

### 5.1. System & Health
* `GET /api/v1/health` — System health check (verifies active connections to PostgreSQL, Qdrant gRPC, and Ollama API).

### 5.2. Document Management
* `POST /api/v1/documents/upload` — Upload a file (`multipart/form-data`). Saves metadata to PostgreSQL (`status: processing`), queues the background indexing task, and returns `202 Accepted`.
* `GET /api/v1/documents` — Fetch a list of all documents and their indexing statuses from PostgreSQL.
* `DELETE /api/v1/documents/{id}` — Delete a document record from PostgreSQL and purge all associated vector points from Qdrant by payload filter.

### 5.3. Chat and RAG Management
* `POST /api/v1/chats` — Initialize a new dialogue session in PostgreSQL.
* `GET /api/v1/chats` — Fetch a list of all chat sessions.
* `GET /api/v1/chats/{id}/history` — Load message history for a specific chat session.
* `DELETE /api/v1/chats/{id}` — Delete a chat session and its message history.
* `POST /api/v1/chats/{id}/message` — Submit a new query.
  * *Payload:* `{ "query": "string", "stream": true }`
  * *Response:* Real-time `text/event-stream` (SSE) or JSON response.

---

## 6. Non-Functional Requirements

### 6.1. Network & Data Isolation
* **Container Isolation:** Only the `gateway` (Nginx) container exposes port `80` to the host machine. PostgreSQL, Qdrant, Ollama, and Rust Backend communicate strictly over the internal Docker bridge network (`internal_network`).
* **Prompt Injection Mitigation:** Clearly delimit user input from system instructions and retrieved context blocks using XML tags (e.g., `<context>...</context>`, `<user_query>...</user_query>`).

### 6.2. Performance & Resource Budgets
* **GPU Utilization:** 100% of model layers must reside in GPU VRAM (`ollama ps` must show `100% GPU`).
* **Latency Targets:**
  * Qdrant gRPC vector search: **< 20 ms**.
  * Time to First Token (TTFT) on warm model: **< 1.5 seconds**.
  * Generation speed: **25–35+ tokens/sec**.
* **Connection Lifecycle:** Properly handle client disconnects during SSE streaming in Tokio to immediately abort ongoing Ollama generation and free GPU compute.

### 6.3. Fault Tolerance & Observability
* Automatic container restarts (`restart: unless-stopped`).
* Structured telemetry in Rust (`tracing` + `tracing-subscriber`) logging execution time for each pipeline stage (parsing, embedding, Qdrant search, LLM TTFT).

---

## 7. Acceptance Criteria

1. The entire stack (`gateway`, `backend`, `postgres`, `qdrant`, `ollama`) launches cleanly with a single command: `docker compose up -d`.
2. `ollama ps` confirms both `qwen2.5:7b-instruct-q4_K_M` and `nomic-embed-text` run at `100% GPU` without exceeding 6 GB VRAM.
3. Uploaded `.txt`, `.md`, `.pdf`, and `.docx` files are processed asynchronously in the background without blocking concurrent chat requests.
4. Chat queries retrieve accurate context from Qdrant and stream tokens smoothly to the client via Nginx without buffering delays.
