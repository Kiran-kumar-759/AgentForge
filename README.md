# AgentForge (ORCA)

**ORCA: Marine EcOsystem Reasoning with Collaborative Agents**

AgentForge is an intelligent geospatial and ecological reasoning platform designed for marine domain awareness, coastal hazard detection, vessel tracking, and environmental monitoring. The system combines real-time oceanographic data ingestion, geospatial analysis, and collaborative LLM-driven reasoning.

---

## 🌟 Key Features

- **Multi-Provider LLM Routing**: Resilient fallback routing across Groq (primary), Google Gemini (fallback #1), and OpenRouter (fallback #2).
- **Geospatial & Marine Ingestion**: Ingestion pipelines for GDACS natural hazard alerts, vessel traffic, WorldPop human exposure data, NOAA ERDDAP sea surface temperature, and Open-Meteo marine forecasts.
- **PostGIS Geospatial Analytics**: High-performance spatial querying (e.g. `ST_DWithin`, coordinate validation, and buffer zones) for exposure and risk assessment.
- **Asynchronous Task Processing**: Celery worker architecture backed by Redis/Valkey for heavy ingestion and reasoning tasks.
- **Modern Interactive Dashboard**: Full-stack web client built with TanStack Start, React 19, Tailwind CSS, Leaflet marine maps, and ReactFlow diagramming.

---

## 🏗️ Architecture Overview

```
AgentForge/
├── backend/                  # FastAPI & Celery backend
│   ├── app/
│   │   ├── api/routes/       # REST API endpoints (data, exposure, LLM, etc.)
│   │   ├── core/             # Configuration, logging, LLM client routers
│   │   ├── db/               # SQLAlchemy models & database sessions
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Geospatial & analytical domain logic
│   │   └── workers/          # Celery background tasks
│   ├── alembic/              # Database schema migrations
│   ├── requirements.txt      # Python dependencies
│   └── seed.py               # Seed scripts for initial datasets
├── frontend/                 # TanStack Start / React 19 web application
│   ├── src/
│   │   ├── api/              # API clients & query endpoints
│   │   ├── components/       # UI components & interactive maps
│   │   └── routes/           # File-based TanStack routing
│   ├── package.json          # Frontend dependencies & scripts
│   └── vite.config.ts        # Vite configuration
└── docs/                     # Technical specifications and phase audit reports
```

---

## 🚀 Getting Started

### Prerequisites

- **Python**: 3.11+
- **Node.js**: 20+ (or Bun)
- **PostgreSQL**: 15+ with PostGIS extension enabled
- **Redis / Valkey**: running on `localhost:6379`

---

### Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your database URL, Redis URL, and LLM API keys
   ```

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Seed foundational metadata**:
   ```bash
   python seed.py
   ```

7. **Start the API server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

8. **Start the Celery worker (in a separate terminal)**:
   ```bash
   celery -A app.workers.celery_app worker --loglevel=info
   ```

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

3. **Install dependencies**:
   ```bash
   npm install
   # or
   bun install
   ```

4. **Start the development server**:
   ```bash
   npm run dev
   # or
   bun dev
   ```

5. Open your browser at [http://localhost:5173](http://localhost:5173).

---

## 🧪 Testing

Run backend test suites:
```bash
cd backend
pytest
```

Run frontend unit tests:
```bash
cd frontend
npm run test
```

---

## 📄 License

This project is licensed under the MIT License.

