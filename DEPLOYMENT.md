# Deployment Guide: Endstate Live Demo

This guide explains how to deploy Endstate to the cloud for a live demo using a **Shared Sandbox** architecture. This approach allows users to use their own Gemini keys while sharing a single Neo4j database with automatic data isolation.

## 1. Database: Shared Neo4j Aura (Free Tier)

1.  Go to [Neo4j Aura](https://neo4j.com/aura/) and create a free account.
2.  Create a "Neo4j AuraDB Free" instance.
3.  **Download the credentials**. You will need:
    *   `Connection URL` (starts with `neo4j+s://`)
    *   `Username` (usually `neo4j`)
    *   `Password`

## 2. LLM: User-Provided Gemini Keys

1.  Get an API key from [Google AI Studio](https://aistudio.google.com/).
2.  Ensure you have access to `gemini-2.0-flash-lite` or similar models.

## 3. Backend: Render (Free Tier)

1.  Create a [Render](https://render.com) account.
2.  Click **New +** > **Web Service**.
3.  Connect your GitHub repository.
4.  Configure the service:
    *   **Runtime**: `Docker`
    *   **Dockerfile Path**: `backend/Dockerfile`
    *   **Docker Context**: `.`
5.  **Set Environment Variables**:
    *   `LLM_PROVIDER`: `gemini`
    *   `NEO4J_URI`: Your Aura connection URL.
    *   `NEO4J_USERNAME`: Your Aura username (usually `neo4j`).
    *   `NEO4J_PASSWORD`: Your Aura password.
    *   `PORT`: `8000`
6.  Deploy! Once live, copy your service URL (e.g., `https://endstate-backend.onrender.com`).

## 4. Frontend: Vercel (Free Tier)

1.  Create a [Vercel](https://vercel.com) account.
2.  Import your GitHub repository.
3.  Framework Preset: `Vite`. 
4.  Root Directory: Click "Edit" and select the `frontend` folder.
5.  Build and Output Settings: Use defaults.
6.  Environment Variables:
    *   `VITE_API_URL`: Paste your Render Backend URL.
7.  Deploy!

## 5. Using the Live Demo

1.  Navigate to your Vercel URL.
2.  You will see a banner asking for a **Gemini API Key**.
3.  Click **Open Settings** and paste a key.
4.  All your data (projects, chat history, knowledge graph) will be automatically isolated from other users via your browser's unique **Session ID**.

---

> [!TIP]
> This "Bring Your Own Key" architecture ensures that the live demo is completely free for the maintainer while keeping user data perfectly isolated.
