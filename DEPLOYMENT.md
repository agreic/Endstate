# Deployment Guide: Endstate Live Demo

> ← Back to [Main README](./README.md)

Deploy Endstate to the cloud using free tiers.

## 1. Database: Neo4j Aura (Free Tier)

1. Go to [Neo4j Aura](https://neo4j.com/aura/) and create a free account
2. Create a "Neo4j AuraDB Free" instance
3. **Download credentials (CSV file)** - you'll need:
   - Connection URL (starts with `neo4j+s://`)
   - Username (usually `neo4j`)
   - Password

## 2. LLM Provider (Choose One)

### Option A: Google Gemini
1. Get an API key from [Google AI Studio](https://aistudio.google.com/)
2. Set `LLM_PROVIDER=gemini` and `GOOGLE_API_KEY=your_key`

### Option B: OpenRouter
1. Get an API key from [OpenRouter](https://openrouter.ai/)
2. Set `LLM_PROVIDER=openrouter` and `OPENROUTER_API_KEY=your_key`

## 3. Backend: Render (Free Tier)

1. Create a [Render](https://render.com) account
2. Click **New +** > **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Docker Context**: `.`
5. Set Environment Variables:
   - `LLM_PROVIDER`: `gemini`
   - `GOOGLE_API_KEY`: (your Gemini API key)
   - `NEO4J_URI`: (your Neo4j Aura connection URL)
   - `NEO4J_USERNAME`: (usually `neo4j`)
   - `NEO4J_PASSWORD`: (your Neo4j password)
   - `PORT`: `8000`
6. Deploy and copy your service URL (e.g., `https://endstate-backend.onrender.com`)

## 4. Frontend: Vercel (Free Tier)

1. Create a [Vercel](https://vercel.com) account
2. Import your GitHub repository
3. Framework Preset: `Vite`, root directory: `frontend`
4. **Environment Variables**:
   - `VITE_API_URL`: (your Render backend URL)
5. Deploy!

## 5. Using the Live Demo

1. Navigate to your Vercel URL
2. If using "Bring Your Own Key" architecture:
   - Click **Open Settings**
   - Paste your **Gemini API Key** and **Neo4j Aura Credentials**
   - Click **Save Changes**
3. Start chatting! Your data is stored privately in your Neo4j Aura instance

---

> [!TIP]
> This "Bring Your Own Key" architecture ensures the live demo is completely free for the maintainer while keeping user data perfectly isolated.
> 
> **Security Note:** All overrides are **request-scoped**. Credentials provided in the UI are sent via headers and managed in memory only for the duration of that specific request. They never modify the global server configuration or affect other users.

## Alternative: Local Development

For local development with Neo4j:

```bash
# Option 1: Use Neo4j Aura (cloud)
# Set environment variables in .env

# Option 2: Run Neo4j locally with Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:latest
```

> [!TIP]
> **Saving Resources**: If you are using Cloud LLMs (Gemini/OpenRouter), you can keep the local Ollama container disabled by not setting `COMPOSE_PROFILES=ollama`.
