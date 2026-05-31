#!/bin/bash
# Project setup script for LLM Red-Team Platform

set -e  # Exit on error

echo "🚀 Setting up LLM Red-Team Platform..."

# Create directory structure
echo "📁 Creating directory structure..."

# Backend structure
mkdir -p backend/{api,models,services,integrations,tests,alembic/versions}
mkdir -p backend/api/{routes,middleware,deps}
mkdir -p backend/services/{model_service,eval_service,auth_service}
mkdir -p backend/integrations/{openai,anthropic,vllm}

# Red-team engine structure
mkdir -p redteam-engine/{adversarial,detection,benchmarks,strategies,metrics,tests}
mkdir -p redteam-engine/adversarial/{generators,templates}
mkdir -p redteam-engine/detection/{jailbreak,hallucination}
mkdir -p redteam-engine/benchmarks/{safety,accuracy,robustness}
mkdir -p redteam-engine/strategies/{injection,toxicity,misinformation}

# Workers
mkdir -p workers/{tasks,utils}

# Frontend structure
mkdir -p frontend/src/{components,pages,charts,hooks,services,utils,types}
mkdir -p frontend/src/components/{dashboard,evaluation,models,results}
mkdir -p frontend/src/pages/{home,evaluations,leaderboard,settings}
mkdir -p frontend/public

# Infrastructure
mkdir -p infrastructure/{docker,k8s,terraform}
mkdir -p infrastructure/docker/{backend,frontend,worker}
mkdir -p infrastructure/k8s/{base,overlays}

# Data & Research
mkdir -p datasets/{adversarial,benchmarks,reference}
mkdir -p research/{notebooks,experiments,papers}

# Scripts & Docs
mkdir -p scripts/{setup,deployment,analysis}
mkdir -p docs/{api,architecture,research}

# Logs & Results
mkdir -p logs
mkdir -p results/{evaluations,analysis}

echo "✅ Directory structure created"

# Create placeholder files
echo "📝 Creating initial files..."

# Backend files
touch backend/__init__.py
touch backend/main.py
touch backend/config.py
touch backend/database.py
touch backend/requirements.txt
touch backend/api/__init__.py
touch backend/models/__init__.py
touch backend/services/__init__.py

# Red-team engine files
touch redteam-engine/__init__.py
touch redteam-engine/core.py
touch redteam-engine/config.py
touch redteam-engine/requirements.txt

# Worker files
touch workers/__init__.py
touch workers/eval_worker.py
touch workers/celeryconfig.py

# Frontend files
touch frontend/package.json
touch frontend/tsconfig.json
touch frontend/vite.config.ts
touch frontend/.env.example
touch frontend/src/main.tsx
touch frontend/src/App.tsx
touch frontend/index.html

# Config files
touch .env.example
touch .gitignore
touch docker-compose.yml
touch Makefile

echo "✅ Initial files created"

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv
*.egg-info/
dist/
build/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnpm-debug.log*
dist/
*.local

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env
.env.local
.env.*.local
*.key
*.pem

# Database
*.db
*.sqlite
*.sqlite3

# Logs
logs/
*.log

# Results & Data
results/
datasets/*.csv
datasets/*.json
!datasets/README.md

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Docker
*.pid

# Misc
.cache/
temp/
tmp/
EOF

echo "✅ .gitignore created"

# Create .env.example
cat > .env.example << 'EOF'
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/llm_redteam
REDIS_URL=redis://localhost:6379/0

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Application
SECRET_KEY=your-secret-key-change-in-production
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Worker Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Model Configuration
VLLM_HOST=http://localhost:8001
DEFAULT_MODEL=gpt-4
MAX_CONCURRENT_EVALS=5

# Frontend
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# Monitoring (optional)
WANDB_API_KEY=
SENTRY_DSN=
EOF

echo "✅ .env.example created"

echo "
🎉 Project structure created successfully!

Next steps:
1. Copy .env.example to .env and configure
2. Set up Python virtual environment: python -m venv venv
3. Install backend dependencies: cd backend && pip install -r requirements.txt
4. Install frontend dependencies: cd frontend && npm install
5. Start Docker services: docker-compose up -d
6. Run database migrations: cd backend && alembic upgrade head

For detailed instructions, see README.md
"
