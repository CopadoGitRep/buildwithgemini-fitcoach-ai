# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import datetime
import json
import os
import urllib.request
from zoneinfo import ZoneInfo

import google.auth
from google import genai
from google.cloud import firestore, storage
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

try:
    from app.a2ui_utils import a2ui_callback
except ImportError:
    from a2ui_utils import a2ui_callback

# IMPORTANT: Hardcoded project ID and Cloud Storage bucket strings
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-6fec44d0cd84"
STORAGE_BUCKET_NAME = "fitcoach-ai-media-qwiklabs-gcp-03-6fec44d0cd84"


def get_firestore_client() -> firestore.Client:
    """Helper function to create a Firestore client with hardcoded project ID and required scopes."""
    creds, _ = google.auth.default(
        scopes=[
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/datastore",
        ]
    )
    return firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=creds)


def get_exercise_catalog(category: str = "") -> str:
    """Fetches exercises from the exercise catalog in Firestore.

    Args:
        category: Optional category filter like 'Legs', 'Chest', 'Back', or 'Shoulders'. If empty, returns all.

    Returns:
        JSON string of exercises from the catalog.
    """
    try:
        db = get_firestore_client()
        docs = db.collection("exercise_catalog").stream()
        catalog = []
        for doc in docs:
            data = doc.to_dict()
            if not category or data.get("category", "").lower() == category.lower():
                catalog.append(data)
        return json.dumps(catalog, indent=2)
    except Exception as e:
        return f"Error reading exercise catalog: {e}"


def get_workout_history(user_id: str = "user_default") -> str:
    """Retrieves logged workout sessions from Firestore for a user.

    Args:
        user_id: ID of the user whose workout history to retrieve.

    Returns:
        JSON string of past workout sessions.
    """
    try:
        db = get_firestore_client()
        docs = db.collection("workout_sessions").stream()
        sessions = []
        for doc in docs:
            data = doc.to_dict()
            if data.get("user_id") == user_id:
                sessions.append(data)
        # Sort by date descending
        sessions.sort(key=lambda s: s.get("date", ""), reverse=True)
        return json.dumps(sessions, indent=2)
    except Exception as e:
        return f"Error retrieving workout history: {e}"


def log_workout_session(
    title: str,
    exercises_summary: str,
    notes: str = "",
    date: str = "",
    user_id: str = "user_default"
) -> str:
    """Logs a completed workout session to Firestore.

    Args:
        title: Title of the workout session (e.g., 'Leg Day Heavy', 'Full Body Strength').
        exercises_summary: Text or JSON summary of exercises performed with sets, reps, and weights.
        notes: Optional user notes or reflections on the session.
        date: Date string (YYYY-MM-DD). If omitted, defaults to today's date.
        user_id: ID of the user logging the workout.

    Returns:
        A confirmation message with the session ID.
    """
    try:
        if not date:
            date = datetime.date.today().isoformat()
        
        db = get_firestore_client()
        session_id = f"session_{int(datetime.datetime.now().timestamp())}"
        session_doc = {
            "id": session_id,
            "user_id": user_id,
            "date": date,
            "title": title,
            "exercises_summary": exercises_summary,
            "notes": notes,
            "created_at": datetime.datetime.now().isoformat()
        }
        db.collection("workout_sessions").document(session_id).set(session_doc)
        return f"Successfully logged workout session '{title}' (ID: {session_id}) for {date}."
    except Exception as e:
        return f"Error logging workout session: {e}"


def calculate_one_rep_max(weight_lbs: float, reps: int) -> str:
    """Calculates estimated 1-Rep Max (1RM) using the Epley formula and training target percentages.

    Args:
        weight_lbs: The weight lifted in pounds.
        reps: The number of repetitions completed.

    Returns:
        A string summarizing the estimated 1RM and key percentage target weights.
    """
    if reps <= 0 or weight_lbs <= 0:
        return "Please provide positive non-zero values for weight and reps."
    if reps == 1:
        one_rm = float(weight_lbs)
    else:
        one_rm = weight_lbs * (1 + reps / 30.0)
    
    one_rm = round(one_rm, 1)
    return (
        f"Estimated 1RM: {one_rm} lbs. "
        f"Target weights: 90% = {round(one_rm * 0.9, 1)} lbs, "
        f"80% = {round(one_rm * 0.8, 1)} lbs, "
        f"70% = {round(one_rm * 0.7, 1)} lbs."
    )


def search_online_exercises(term: str = "") -> str:
    """Queries the free wger Workout Manager public API for online exercise details and muscle groups.

    Args:
        term: Optional search term or category to filter exercises (e.g., 'Press', 'Squat', 'Shoulders').

    Returns:
        JSON string of exercise details from the wger public API.
    """
    try:
        url = "https://wger.de/api/v2/exerciseinfo/?limit=10"
        headers = {"User-Agent": "FitCoach-AI/1.0"}
        
        # Read API key from environment variable if configured
        api_key = os.getenv("WGER_API_KEY")
        if api_key:
            headers["Authorization"] = f"Token {api_key}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        results = []
        for item in data.get("results", []):
            name = ""
            desc = ""
            for trans in item.get("translations", []):
                if trans.get("language") == 2:  # English
                    name = trans.get("name")
                    desc = trans.get("description_source")
                    break
            if not name and item.get("translations"):
                name = item["translations"][0].get("name", "")
                desc = item["translations"][0].get("description_source", "")

            category = item.get("category", {}).get("name", "") if isinstance(item.get("category"), dict) else ""
            muscles = [m.get("name", "") for m in item.get("muscles", []) if isinstance(m, dict)]

            if term and term.lower() not in name.lower() and term.lower() not in category.lower():
                continue

            results.append({
                "name": name,
                "category": category,
                "muscles": muscles,
                "description": desc[:150] if desc else ""
            })
            if len(results) >= 3:
                break

        return json.dumps(results if results else data.get("results", [])[:3], indent=2)
    except Exception as e:
        return f"Error fetching online exercises: {e}"


async def generate_exercise_image(prompt: str, tool_context: ToolContext) -> str:
    """Generates an image for an exercise or fitness graphic using gemini-3.1-flash-lite-image model in global region.

    Saves the image bytes as a session artifact for the Playground and uploads it to the public Cloud Storage bucket.

    Args:
        prompt: Detailed description of the exercise or fitness graphic to generate (e.g., 'Barbell squat anatomical diagram').
        tool_context: ADK ToolContext provided by the framework.

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage (https://storage.googleapis.com/<bucket>/<object>).
    """
    try:
        # 1. Generate image using gemini-3.1-flash-lite-image in global location
        genai_client = genai.Client(vertexai=True, location="global")
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"Generate a clear, high-quality fitness illustration for: {prompt}",
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return "Error: Model did not return image bytes."

        ext = "png" if "png" in mime_type else "jpg"
        timestamp = int(datetime.datetime.now().timestamp())
        filename = f"exercise_image_{timestamp}.{ext}"

        # 2. Save artifact to ToolContext for Playground Artifacts panel
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        try:
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception as artifact_err:
            print(f"Warning saving artifact: {artifact_err}")

        # 3. Upload image bytes directly to GCS bucket (no local file)
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{filename}"
        return public_url

    except Exception as e:
        return f"Error generating exercise image: {e}"


async def generate_exercise_video(prompt: str, tool_context: ToolContext) -> str:
    """Generates a short video for an exercise or fitness demonstration using Google's Omni model (gemini-omni-flash-preview) in global region.

    Saves the video bytes as a session artifact for the Playground and uploads it to the public Cloud Storage bucket.

    Args:
        prompt: Detailed description of the exercise demonstration or fitness video to generate (e.g., 'Barbell squat form demonstration video').
        tool_context: ADK ToolContext provided by the framework.

    Returns:
        The public HTTPS URL of the uploaded video in Cloud Storage (https://storage.googleapis.com/<bucket>/<object>).
    """
    try:
        genai_client = genai.Client(vertexai=True, location="global")
        video_bytes = None
        mime_type = "video/mp4"

        for model_name in ["gemini-omni-flash-preview", "veo-3.1-generate-001"]:
            try:
                op = genai_client.models.generate_videos(
                    model=model_name,
                    prompt=f"Generate a clear, high-quality fitness video demonstration for: {prompt}",
                )
                while not op.done:
                    await asyncio.sleep(4)
                    op = genai_client.operations.get(op)
                
                res = getattr(op, "response", None) or getattr(op, "result", None)
                if res and hasattr(res, "generated_videos") and res.generated_videos:
                    for gv in res.generated_videos:
                        if hasattr(gv, "video") and getattr(gv.video, "video_bytes", None):
                            video_bytes = gv.video.video_bytes
                            mime_type = getattr(gv.video, "mime_type", None) or "video/mp4"
                            break
                if video_bytes:
                    break
            except Exception as e:
                print(f"Model {model_name} video generation attempt error: {e}")

        if not video_bytes:
            return "Error: Could not generate video bytes."

        timestamp = int(datetime.datetime.now().timestamp())
        filename = f"exercise_video_{timestamp}.mp4"

        # 1. Save artifact to ToolContext for Playground Artifacts panel
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        try:
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception as artifact_err:
            print(f"Warning saving video artifact: {artifact_err}")

        # 2. Upload video bytes directly to GCS bucket (no local file)
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{filename}"
        return public_url

    except Exception as e:
        return f"Error generating exercise video: {e}"


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


# WRITE: send session events to Memory Bank for extraction after each turn
async def generate_memories_callback(callback_context: CallbackContext):
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        print(f"Memory extraction note: {e}")
    return None


def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project=FIRESTORE_PROJECT_ID,
        location="us-central1",
        agent_engine_id="2594842493749035008",
    )


# Read Agent Engine resource name from deployment_metadata.json if available
_agent_engine_resource_name = None
_metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
if os.path.exists(_metadata_path):
    try:
        with open(_metadata_path, "r") as _f:
            _meta = json.load(_f)
            _runtime_id = _meta.get("remote_agent_runtime_id")
            if _runtime_id and _runtime_id != "None":
                _agent_engine_resource_name = _runtime_id
    except Exception:
        pass


# Build system prompt with A2uiSchemaManager (version 0.8) and Basic Catalog
_schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

_a2ui_instruction = _schema_manager.generate_system_prompt(
    role_description=(
        "FitCoach AI is an intelligent personal workout coach and fitness assistant. "
        "FitCoach AI remembers and tracks all user workout recommendations, fitness preferences, goals, and workout history across conversations. "
        "Always reference past recommendations and user progress to personalize your guidance."
    ),
    workflow_description=(
        "Analyze the request and return structured UI when appropriate. You can look up exercises from the catalog, "
        "log completed workout sessions, retrieve past workout history from Firestore, generate exercise graphics, "
        "and execute Python code in a secure sandbox to analyze workout data, trends, and calculations."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=_a2ui_instruction,
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=_agent_engine_resource_name
    ),
    tools=[
        PreloadMemoryTool(),
        get_exercise_catalog,
        get_workout_history,
        log_workout_session,
        calculate_one_rep_max,
        search_online_exercises,
        generate_exercise_image,
        generate_exercise_video,
        get_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)

