# 🚀 Multi-Agent LLM Orchestrator with HITL and Real-Time Streaming

## 📌 Overview

This project is a **production-grade multi-agent AI system** designed to orchestrate multiple Large Language Models (LLMs) into a structured, intelligent pipeline. It transforms a simple user query into a **multi-stage reasoning process** involving planning, research, drafting, critique, and refinement — all enhanced with **Human-in-the-Loop (HITL)** feedback and real-time streaming.

Unlike traditional single-model applications, this system demonstrates how modern AI systems are evolving into **modular, agent-driven architectures** capable of iterative improvement, transparency, and scalability.

---
![Architecture Diagram](https://github.com/rahmasaber123/Production-Multi-Agent-AI-Orchestrator/blob/main/project_archiecture/d57c01c5-25b6-4bbe-a0d7-86c8f40c3a6a.png?raw=true)
## 🧠 Core Idea

Instead of relying on a single LLM response, this system breaks down problem-solving into specialized agents:

```
User Query
   ↓
Planner → Researcher → Writer → Critic
   ↓
(Human Feedback Optional - HITL)
   ↓
Finalizer → Final Answer
```

This design enables:

* Structured reasoning
* Reduced hallucinations
* Iterative refinement
* Human-guided intelligence

---

## ⚙️ System Architecture

### 🔹 Backend (FastAPI)

* Handles API requests, streaming, authentication, and orchestration triggers
* Implements async architecture for scalability

### 🔹 Orchestrator (LangGraph)

* Defines the **agent workflow graph**
* Manages execution flow and decision logic
* Implements **looping between Writer and Critic**

### 🔹 Task Service

* Manages task lifecycle (creation, execution, persistence)
* Handles **background execution + streaming + HITL pause/resume**
* Bridges API ↔ Orchestrator ↔ Database

### 🔹 Database (PostgreSQL)

* Stores:

  * user queries
  * intermediate outputs (plan, draft, critique)
  * final answers
* Enables **stateful AI workflows**

### 🔹 Redis

* Supports:

  * rate limiting
  * caching (future-ready)
  * real-time event handling

### 🔹 Frontend

* Displays real-time streaming responses
* Allows user feedback injection (HITL)

---

## 🤖 Multi-Agent Design

Each agent has a specialized responsibility:

| Agent      | Role                                                |
| ---------- | --------------------------------------------------- |
| Planner    | Breaks down the problem into structured steps       |
| Researcher | Gathers categorized knowledge (cost, privacy, etc.) |
| Writer     | Generates the initial draft                         |
| Critic     | Evaluates quality, detects issues, assigns score    |
| Finalizer  | Produces the polished final answer                  |

---

## 🔁 Iterative Refinement Loop

The system includes a feedback loop:

```
Writer → Critic → (score < threshold) → Writer (again)
```

This ensures:

* Higher quality output
* Reduced hallucinations
* Self-improving responses

---

## 🧑‍💻 Human-in-the-Loop (HITL)

A key feature of this system is **human intervention during execution**.

### 🔥 How it works:

1. Pipeline runs until draft is generated
2. System pauses (`awaiting_feedback`)
3. User reviews output
4. User submits feedback
5. Pipeline resumes with human guidance

### 💡 Why it matters:

* Aligns AI output with user intent
* Enables correction before finalization
* Critical for real-world AI systems

---

## ⚡ Real-Time Streaming (SSE)

The system streams execution in real-time using **Server-Sent Events (SSE)**:

* Shows agent-by-agent progress
* Streams partial outputs (token-level)
* Improves UX and transparency

---

## 🔐 Security Features

* **Token-based authentication**
* **Rate limiting (per IP)**
* Protection against:

  * abuse
  * API overuse
  * unauthorized access

---

## 🗄️ Data Model (ORM)

The system uses SQLAlchemy ORM to store full pipeline state:

* question
* plan
* research notes
* draft
* critique
* final answer
* iterations
* timestamps

This enables:

* tracking
* debugging
* analytics
* recovery

---

## 🧩 Technologies Used

### 🔹 AI & LLM Stack

* LangChain
* LangGraph
* OpenAI (GPT-4o)
* Groq (LLaMA-based models)
* Ollama (local LLM support)

### 🔹 Backend

* FastAPI (async API framework)
* Pydantic (validation & schemas)
* SQLAlchemy (ORM)

### 🔹 Infrastructure

* PostgreSQL (persistent storage)
* Redis (caching & rate limiting)
* Docker & Docker Compose

### 🔹 Observability

* Structured logging (JSON)
* LangSmith tracing (optional)

---

## 🐳 Containerization

The entire system is containerized using Docker:

```
Frontend → Backend → PostgreSQL + Redis
```

Benefits:

* reproducibility
* environment consistency
* easy deployment
* scalability

---

## 📡 API Features

* `POST /generate` → async task creation
* `GET /stream` → real-time streaming
* `POST /feedback` → HITL interaction
* `GET /tasks/{id}` → task retrieval
* `GET /health` → system health check

---

## 🚀 Key Highlights

✅ Multi-agent AI architecture
✅ Human-in-the-loop integration
✅ Real-time streaming (SSE)
✅ Async scalable backend
✅ Multi-LLM provider support
✅ Structured outputs (no randomness)
✅ Full task lifecycle tracking
✅ Dockerized production setup

---

## 🧠 What Makes This Project Strong

This is not just an AI demo — it's a **complete production-ready AI system** that demonstrates:

* Agent-based AI design
* Distributed system thinking
* Real-time processing
* Human-AI collaboration
* Scalable backend engineering

---

## 📌 Conclusion

This project represents a modern approach to building AI systems:

> From single-response models → to structured, collaborative, and controllable AI pipelines.

It showcases how to bridge:

* **AI intelligence**
* **software engineering**
* **system design**

into one cohesive, production-ready solution.

---

## 🧑‍💻 Author
Rahma Saber Abbas 
ai engineer 

---
