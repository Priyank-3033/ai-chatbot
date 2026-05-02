# AI-Powered Chatbot for Customer Support

AI-Powered Chatbot for Customer Support is a full-stack web application built with React, Vite, FastAPI, Python, SQLite, and LLM-powered retrieval. It is designed to automate customer interactions, answer FAQs, support troubleshooting, retrieve information from uploaded documents, and assist with ecommerce-style product discovery, wishlist, cart, and order workflows.

The system combines a modern shopping-inspired frontend with an AI backend that supports streaming responses, chat memory, document-aware answers, and protected user sessions. The goal is to improve support speed, reduce repetitive manual work, and deliver more accurate, context-aware assistance.

## Highlights

- AI-powered customer support chat
- FastAPI backend with protected APIs
- React frontend with dedicated chat and store pages
- LLM response generation with streaming support
- JWT-based signup, login, and session protection
- Saved chat sessions per user
- PDF/text upload with retrieval-aware answers
- Persistent vector-style RAG over uploaded documents
- Product discovery, wishlist, cart, checkout, and order tracking
- Admin stats, chat logs, and uploaded document visibility

## Tech Stack

### Frontend
- React
- Vite
- Zustand
- React Markdown

### Backend
- FastAPI
- Python
- SQLite
- OpenAI API / Gemini API support
- PyJWT
- PyPDF
- Persistent vector retrieval store

## Features

### AI and Support
- Instant AI answers for customer support-style questions
- Model selection: `gpt-4o`, `gpt-4o-mini`, and Gemini options
- Streaming chat responses
- Saved conversation memory per chat session
- Document-aware answers using uploaded PDFs/text files
- Prompt-based support and general chat modes
- Voice input and markdown rendering
- Fallback support when a provider is unavailable

### Customer Support + Ecommerce
- Product listing with real photo support
- Search, autocomplete, category filter, and pagination
- Product detail modal
- Wishlist, cart, checkout, and order tracking
- Product recommendation support from chat and catalog APIs
- Support-oriented answers for login, refund, order, and troubleshooting flows

### Auth and Persistence
- Register and login
- JWT authentication
- Protected backend APIs
- Saved chat sessions per user
- Backend persistence for cart, wishlist, orders, and uploaded documents

### Admin
- Product management
- Admin dashboard stats
- Recent chat log visibility
- Uploaded document list

## Recommended Architecture

```text
backend/
  app/
    main.py
    core/
    dependencies.py
    models.py
    data/
    routes/
    services/
frontend/
  src/
    App.jsx
    components/
    hooks/
    services/
    store/
    utils/
render.yaml
README.md
```

## Project Definition

```text
AI-Powered Chatbot for Customer Support

Recommended Tech:
React (frontend) + FastAPI backend + Python (LLM / retrieval pipeline) + Vector DB

Description:
The AI-Powered Chatbot for Customer Support is a web-based application designed to automate customer interactions using AI and Large Language Models (LLMs). The system provides instant responses to customer queries, handles FAQs, assists in troubleshooting, supports information retrieval from uploaded documents, and helps with ecommerce-related guidance such as product discovery, wishlist, cart, and order support.
```

## Environment Variables

### Backend

Use [D:\codex ai\backend\.env.example](D:\codex ai\backend\.env.example)

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
CORS_ORIGINS=http://localhost:5173
AUTH_SECRET=change-me-dev-secret
AUTH_TOKEN_TTL_HOURS=72
DATABASE_PATH=./app_data.sqlite3
ADMIN_EMAILS=admin@smartcommerce.ai
VECTOR_STORE_PATH=./rag_store
EMBEDDING_MODEL_NAME=text-embedding-3-small
```

### Frontend

Use [D:\codex ai\frontend\.env.example](D:\codex ai\frontend\.env.example)

```env
VITE_API_URL=http://127.0.0.1:8000
# Backward-compatible alias also supported:
# VITE_API_BASE_URL=http://127.0.0.1:8000
# Production example:
# VITE_API_URL=https://your-backend-name.onrender.com
```

## Product Images

Product images are resolved in this order:

1. Backend-served local files at `/product-photos/...`
2. Remote product image URLs from the catalog
3. Generated fallback art when neither exists

Local image root:
- [D:\codex ai\frontend\public\product-photos](D:\codex ai\frontend\public\product-photos)

The backend serves local product photos through FastAPI static files, so the same image paths work in development and deployment.

## Screenshots

Keep screenshots in:
- `docs/screenshots/`

Recommended files:
- `docs/screenshots/login.png`
- `docs/screenshots/chat.png`
- `docs/screenshots/store.png`
- `docs/screenshots/product-modal.png`
- `docs/screenshots/admin.png`

Use these screenshots before sharing with recruiters:
- login page
- main chat UI
- store and orders workspace
- product detail modal
- admin dashboard

## Local Setup

### Backend

```powershell
cd "D:\codex ai\backend"
py -3.12 -m pip install -r requirements.txt
py -3.12 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd "D:\codex ai\frontend"
npm install
npm run dev
```

Local URLs:
- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend health: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

## Deployment

### Frontend on Vercel

Config file:
- [D:\codex ai\frontend\vercel.json](D:\codex ai\frontend\vercel.json)

Steps:
1. Push this repo to GitHub
2. Import the `frontend` folder into Vercel
3. Set `VITE_API_URL` to your Render backend URL
4. Deploy

### Backend on Render

Config file:
- [D:\codex ai\render.yaml](D:\codex ai\render.yaml)

Steps:
1. Push this repo to GitHub
2. Create a new Render web service for `backend`, or deploy with `render.yaml`
3. Add environment variables:
   - `OPENAI_API_KEY`
   - `CORS_ORIGINS=https://your-frontend-url.vercel.app`
   - `AUTH_SECRET`
   - `VECTOR_STORE_PATH=./rag_store`
   - `EMBEDDING_MODEL_NAME=text-embedding-3-small`
4. Deploy

### Quick Deploy Order

1. Deploy backend on Render first
2. Copy the Render URL
3. Add that URL to `VITE_API_URL` in Vercel
4. Deploy frontend on Vercel
5. Update Render `CORS_ORIGINS` to your final Vercel URL
6. Re-deploy backend if needed

## Public Deployment Checklist

Before calling the project public/live:

1. Deploy backend on Render
2. Deploy frontend on Vercel
3. Set frontend env:
   - `VITE_API_URL=https://your-backend-name.onrender.com`
4. Set backend env:
   - `OPENAI_API_KEY`
   - `CORS_ORIGINS=https://your-frontend-name.vercel.app`
   - `AUTH_SECRET`
5. Make sure Render keeps persistent storage for:
   - `DATABASE_PATH`
   - `VECTOR_STORE_PATH`
6. Test:
   - signup/login
   - streaming chat
   - product APIs
   - PDF upload
   - RAG answers after upload

## Live Demo

Add real public links here after deployment:

- Frontend: `https://your-frontend-url.vercel.app`
- Backend API: `https://your-backend-url.onrender.com`
- Health check: `https://your-backend-url.onrender.com/api/health`

## Backend Architecture

The backend is split into clear route and service layers:

- `app/main.py`
  - FastAPI setup
  - CORS
  - request logging
  - rate limiting
  - static photo serving
  - router registration
- `app/dependencies.py`
  - shared services and helpers
- `app/routes/`
  - `system.py`
  - `auth.py`
  - `products.py`
  - `commerce.py`
  - `chat.py`
  - `documents.py`
  - `admin.py`
  - `realtime.py`
- `app/services/`
  - auth
  - chatbot
  - database
  - document_service
  - knowledge_base
  - product_catalog

## Production Notes

- SQLite is fine for local development and demos
- For a real public production deployment, PostgreSQL is recommended
- Add a stronger rate limiter and centralized logging for production
- Replace local file storage with cloud storage if uploads grow
- Keep `.env` files out of Git

## Portfolio Summary

```text
AI-Powered Chatbot for Customer Support built with React, FastAPI, Python, and a retrieval-aware vector-backed data layer. The project combines AI chat, document-aware answers, chat memory, authentication, and ecommerce-style customer support workflows in one full-stack application.
```

## Demo Checklist

Before showing the project:

1. Set `OPENAI_API_KEY`
2. Start backend
3. Start frontend
4. Register a user
5. Test chat
6. Upload a PDF or text file
7. Add products to cart
8. Place an order
9. Open order tracking
10. Review admin dashboard

## Recommended Next Steps

1. Move from SQLite to PostgreSQL
2. Add stronger RAG over uploaded docs and support docs
3. Add tests for backend APIs and chat flows
4. Deploy live and replace the placeholder links above
