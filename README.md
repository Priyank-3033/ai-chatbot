# Smart AI Commerce Chatbot

A full-stack AI commerce app with:
- real OpenAI-backed chat when an API key is available
- fallback answer system for offline or quota-limited cases
- user login with backend auth
- saved chat sessions
- product catalog, wishlist, cart, checkout, and order tracking
- compact chat + store UI

## Stack

Frontend:
- React
- Vite

Backend:
- FastAPI
- SQLite
- OpenAI API
- Static product photo serving

## Features

### AI
- `gpt-4o` / `gpt-4o-mini` model selection
- custom prompt support
- prompt presets
- memory across the current session
- typing animation
- markdown rendering
- file upload context
- backend document upload for PDF/text files
- document-aware answers using simple RAG-style retrieval
- realtime WebSocket chat streaming foundation
- voice input
- fallback answers for support, study, coding, career, daily life, travel, business, and health topics

### Commerce
- product listing
- debounced search
- autocomplete suggestions
- category filtering
- pagination
- product detail modal
- wishlist
- cart
- checkout
- order history
- order tracking
- admin product management

### Auth and persistence
- register/login with backend
- JWT authentication flow
- saved chat sessions per user
- cart, wishlist, and orders stored in backend database

### Admin
- product management
- admin stats
- recent chat logs
- uploaded document visibility

### Production-ready backend improvements
- structured route modules
- FastAPI static file serving for product photos
- request logging
- basic in-memory rate limiting

## Project Structure

```text
backend/
  app/
    main.py
    config.py
    dependencies.py
    models.py
    data/
    routes/
    services/
frontend/
  src/
    App.jsx
    components/
    utils/
```

## Environment Variables

### Backend: `backend/.env`

Use [D:\codex ai\backend\.env.example](D:\codex ai\backend\.env.example)

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
CORS_ORIGINS=http://localhost:5173
AUTH_SECRET=change-me-dev-secret
AUTH_TOKEN_TTL_HOURS=72
DATABASE_PATH=./app_data.sqlite3
ADMIN_EMAILS=admin@smartcommerce.ai
```

### Frontend: `frontend/.env`

Use [D:\codex ai\frontend\.env.example](D:\codex ai\frontend\.env.example)

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Product Images

- Product images can come from:
  1. backend-served local files at `/product-photos/...`
  2. remote image URLs from the product catalog
  3. generated fallback art when neither exists

- Local image root:
  - [D:\codex ai\frontend\public\product-photos](D:\codex ai\frontend\public\product-photos)

- Backend now serves that folder directly through FastAPI static files, so local images work consistently in development and production.

## Screenshots

Recommended screenshots to add before publishing:
- Login page
- Smart Chat page
- Store and orders page
- Product detail modal
- Cart / checkout flow

Suggested folder:
- `docs/screenshots/`

Example filenames:
- `docs/screenshots/login.png`
- `docs/screenshots/chat.png`
- `docs/screenshots/store.png`
- `docs/screenshots/product-modal.png`

## Local Setup

### 1. Backend

```powershell
cd "D:\codex ai\backend"
py -3.12 -m pip install -r requirements.txt
py -3.12 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 2. Frontend

```powershell
cd "D:\codex ai\frontend"
npm install
npm run dev
```

Frontend:
- [http://localhost:5173](http://localhost:5173)

Backend health:
- [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

## Live Deployment

## Frontend on Vercel

Files added:
- [D:\codex ai\frontend\vercel.json](D:\codex ai\frontend\vercel.json)

Steps:
1. Push the repo to GitHub
2. Import the `frontend` folder into Vercel
3. Set environment variable:
   - `VITE_API_BASE_URL=https://your-backend-url.onrender.com`
4. Deploy
5. Copy the live frontend URL and add it under the `Live Demo` section below

## Backend on Render

Files added:
- [D:\codex ai\render.yaml](D:\codex ai\render.yaml)

Steps:
1. Push the repo to GitHub
2. Create a new Render Web Service for the `backend` folder
3. Or use Blueprint deploy with `render.yaml`
4. Add environment variables:
   - `OPENAI_API_KEY`
   - `CORS_ORIGINS=https://your-frontend-url.vercel.app`
5. Deploy
6. Copy the live backend URL and update `VITE_API_BASE_URL` in Vercel if needed

## Live Demo

Add your live links here after deployment:

- Frontend: `https://your-frontend-url.vercel.app`
- Backend API: `https://your-backend-url.onrender.com`
- Health check: `https://your-backend-url.onrender.com/api/health`

### Important production note
- Current app uses SQLite
- SQLite is fine for local use and small demos
- For a real public production app, move to PostgreSQL

## Backend Structure

The backend is now split into clear route and service layers:

- `app/main.py`
  - FastAPI app setup
  - CORS
  - static file mounting for product photos
  - router registration
- `app/dependencies.py`
  - shared services
  - auth helpers
  - response builders
- `app/routes/`
  - `system.py`
  - `auth.py`
  - `products.py`
  - `commerce.py`
  - `chat.py`
  - `admin.py`
- `app/services/`
  - auth
  - chatbot
  - database
  - knowledge base
  - product catalog

## Recommended Production Upgrades

- move database from SQLite to PostgreSQL
- add rate limiting
- add stronger auth/session management
- add server-side file storage for uploads
- add real RAG over uploaded docs or support docs
- add monitoring and logging

## What is already improved in this repo

- real OpenAI client integration in backend
- static image serving from FastAPI
- structured service-based backend organization
- env-based API key handling
- JWT auth for login and protected APIs
- chat history and session persistence
- loading/error handling in chat flow
- compact UI with chat/store tabs
- deployment starter files for Vercel and Render

## Demo Checklist

Before showing the project:
1. Set `OPENAI_API_KEY`
2. Start backend
3. Start frontend
4. Register a user
5. Test chat
6. Add products to cart
7. Place an order
8. Open order tracking

## Next recommended steps

1. PostgreSQL migration
2. Real document RAG
3. Better analytics and admin insights
4. Live deployed links added here
