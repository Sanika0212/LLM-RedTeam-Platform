# Quick Start Guide - LLM Red-Team Platform

## 🚀 Get Started in 5 Minutes

### Prerequisites
```bash
# Required
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

# Optional (for local model serving)
- CUDA-capable GPU
```

### Step 1: Initial Setup
```bash
# Clone/extract the project
cd llm-redteam-platform

# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

### Step 2: Start Infrastructure
```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to be healthy (about 10 seconds)
docker-compose ps
```

### Step 3: Backend Setup
```bash
# Install dependencies
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn main:app --reload

# Backend now running at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Step 4: Frontend Setup (New Terminal)
```bash
cd frontend
npm install
npm run dev

# Frontend now running at http://localhost:3000
```

### Step 5: Start Worker (New Terminal)
```bash
cd backend
source venv/bin/activate
celery -A workers.eval_worker worker --loglevel=info
```

### Step 6: Test the System
```bash
# Visit http://localhost:3000
# Register a new account
# Create your first evaluation
# Watch results appear in real-time!
```

---

## 🐳 Docker Method (Alternative)

If you prefer to run everything in Docker:

```bash
# Start all services at once
make up

# Check status
make ps

# View logs
make logs

# Access services
# - Backend: http://localhost:8000
# - Frontend: http://localhost:3000
# - API Docs: http://localhost:8000/docs
```

---

## 🎯 Your First Evaluation

1. **Login** at http://localhost:3000
2. **Navigate to** "New Evaluation"
3. **Select Model:** GPT-4 or Claude
4. **Choose Benchmark:** "Safety Test" preset
5. **Click Submit** and watch the magic happen!

---

## 📖 What to Read Next

1. **README.md** - Full project overview
2. **docs/PROJECT_KICKOFF.md** - Project vision and next steps
3. **docs/VAISHAK_TASKS.md** - Red-teaming work breakdown
4. **docs/SANIKA_TASKS.md** - Platform work breakdown
5. **docs/TIMELINE.md** - 12-week project plan

---

## 🔧 Common Commands

```bash
# View all available commands
make help

# Run tests
make test

# Format code
make format

# Check service health
make health

# View database
make shell-db

# View Redis
make redis-cli
```

---

## ❓ Troubleshooting

**Problem:** Docker containers won't start  
**Solution:** Make sure ports 5432, 6379, 8000, 3000 are free

**Problem:** Database migration fails  
**Solution:** Run `make clean` then `make up` to reset

**Problem:** Frontend can't connect to backend  
**Solution:** Check `.env` has correct `VITE_API_URL`

**Problem:** Worker not processing jobs  
**Solution:** Check Redis is running: `make redis-cli` then `PING`

---

## 🆘 Need Help?

- Check the main **README.md** for detailed documentation
- Review **docs/PROJECT_KICKOFF.md** for setup guidance
- See task breakdowns in **docs/** for specific components

---

**Ready to build something amazing? Let's go! 🚀**
