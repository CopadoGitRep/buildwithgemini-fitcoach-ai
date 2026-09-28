# FitCoach AI 🏋️

An intelligent, personal workout coach and fitness assistant built with Google Agent Development Kit (ADK), Gemini models, and Google Cloud platform services.

![FitCoach AI Demo](demo.gif)

---

## 🌟 Overview

**FitCoach AI** is an end-to-end fitness assistant that offers exercise recommendations, workout session logging, 1RM calculations, and media generation. Built on top of Google's Agent Development Kit (ADK 1.1.0) and deployed to Vertex AI Agent Runtime, FitCoach AI provides a responsive, multi-modal chat experience featuring structured **A2UI cards** and custom frontend components.

---

## 🚀 Woven Capabilities & Services

The agent's capabilities are implemented across the `app/` modules and `agents-cli-manifest.yaml`:

### 🧠 Cross-Session Memory Bank
- **Vertex AI Memory Bank**: Integrated using `VertexAiMemoryBankService` and `PreloadMemoryTool`.
- **Automatic Memory Persistence**: Post-turn session callbacks automatically write key fitness preferences, past workout context, and goals across sessions.

### 🗄️ Database & Storage Integrations
- **Google Cloud Firestore**: Persists user workout logs (`log_workout_session`) and retrieves session history (`get_workout_history`) from the `workouts` collection.
- **Google Cloud Storage (GCS)**: Stores generated media assets in a dedicated public GCS bucket (`fitcoach-ai-media-qwiklabs-gcp-03-6fec44d0cd84`).

### 🎨 Generative Media Tools
- **Exercise Image Generation (`generate_exercise_image`)**: Generates fitness diagrams using `gemini-3.1-flash-lite-image`, uploading image bytes directly to Cloud Storage and returning public HTTPS URLs.
- **Exercise Video Generation (`generate_exercise_video`)**: Generates exercise demonstration videos using Google's Omni model (`gemini-omni-flash-preview`) in the `global` region, saving artifacts to the ADK session and uploading to Cloud Storage.

### 🖥️ Rich A2UI Interface Protocol
- **A2UI Card Renderer**: Uses `A2uiSchemaManager` and `BasicCatalog` (`a2ui_callback`) to return interactive JSON display cards (headings, lists, metrics, columns, rows, images).
- **Custom Chat Web UI**: Lightweight FastAPI proxy and HTML5/CSS3 frontend featuring theme styling, timestamping, quick-prompt chips, and message copy utilities.

### 🔒 Code Sandbox & Custom Tools
- **Code Execution Sandbox**: Runs calculations safely using `AgentEngineSandboxCodeExecutor`.
- **Fitness & Utility Tools**:
  - `get_exercise_catalog`: Catalog lookup filtered by targeted muscle group and difficulty.
  - `log_workout_session`: Writes workout details directly to Firestore.
  - `get_workout_history`: Queries recent logged workout entries.
  - `calculate_one_rep_max`: Computes estimated 1RM using Epley's formula ($1RM = w \times (1 + r / 30)$).
  - `search_online_exercises`: Retrieves external exercise information using web search.
  - `get_weather` & `get_current_time`: Location and time utilities.

---

## 🛠️ Project Structure

```
fitcoach-ai/
├── README.md                  # Project documentation
├── demo.gif                   # Looping interaction demo recording
├── agents-cli-manifest.yaml   # ADK agent manifest (Python, us-east1, Agent Runtime)
├── deployment_metadata.json   # Deployment resource configuration
├── app/
│   ├── __init__.py            # App module export
│   ├── agent.py               # Root ADK agent configuration, tools, and callbacks
│   └── a2ui_utils.py          # A2UI callback and schema transformer
└── frontend/
    ├── main.py                # FastAPI proxy server (A2A protocol bridge)
    ├── requirements.txt       # Frontend dependencies
    └── static/
        └── index.html         # Custom chat user interface & A2UI renderer
```

---

## 💻 Local Setup & Execution

### 1. Prerequisites
- **Python**: Python 3.11+
- **Google Cloud SDK**: `gcloud` CLI installed and authenticated with `roles/aiplatform.user`

### 2. Running the Agent Backend

Install dependencies using `uv` (or `pip`):

```bash
uv pip install -r requirements.txt
```

Launch the local ADK developer playground:

```bash
adk web app/
```

### 3. Running the Web Frontend

Navigate to the `frontend/` directory and install its requirements:

```bash
cd frontend
uv pip install -r requirements.txt
```

Set the required environment variables pointing to your Agent Engine deployment and directory:

```bash
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_ID>/locations/<LOCATION>/reasoningEngines/<ENGINE_ID>"
export AGENT_DIRECTORY="app"
```

Start the FastAPI server:

```bash
uv run python main.py
```

---

## ☁️ Cloud Deployment

To deploy the agent to Vertex AI Agent Runtime:

```bash
agents-cli deploy
```

To deploy the frontend proxy to Google Cloud Run:

```bash
gcloud run deploy fitcoach-frontend \
  --source=frontend/ \
  --region=us-east1 \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<RESOURCE_NAME>",AGENT_DIRECTORY="app" \
  --allow-unauthenticated
```
