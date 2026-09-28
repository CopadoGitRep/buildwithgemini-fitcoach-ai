# Seed script for FitCoach AI Firestore collection
import google.auth
from google.cloud import firestore

# IMPORTANT: Hardcoded Project ID string (do not use GOOGLE_CLOUD_PROJECT or google.auth.default() for project ID)
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-6fec44d0cd84"

def get_firestore_client():
    creds, _ = google.auth.default(
        scopes=[
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/datastore",
        ]
    )
    return firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=creds)

def seed_database():
    db = get_firestore_client()

    # Clean up temporary test doc if present
    db.collection("exercise_catalog").document("test").delete()

    # 1. Seed Exercise Catalog Collection
    exercise_ref = db.collection("exercise_catalog")
    exercises = [
        {
            "id": "barbell_squat",
            "name": "Barbell Squat",
            "category": "Legs",
            "target_muscle": "Quadriceps & Glutes",
            "difficulty": "Intermediate",
            "equipment": "Barbell, Squat Rack",
            "description": "Squat down with barbell on upper back until thighs are parallel to ground."
        },
        {
            "id": "bench_press",
            "name": "Barbell Bench Press",
            "category": "Chest",
            "target_muscle": "Pectoralis Major & Triceps",
            "difficulty": "Intermediate",
            "equipment": "Barbell, Flat Bench",
            "description": "Lower bar to chest and press upwards explosively."
        },
        {
            "id": "pull_ups",
            "name": "Bodyweight Pull-Ups",
            "category": "Back",
            "target_muscle": "Latissimus Dorsi & Biceps",
            "difficulty": "Intermediate",
            "equipment": "Pull-up Bar",
            "description": "Pull body up until chin clears the bar."
        },
        {
            "id": "overhead_press",
            "name": "Overhead Barbell Press",
            "category": "Shoulders",
            "target_muscle": "Deltoids & Triceps",
            "difficulty": "Intermediate",
            "equipment": "Barbell",
            "description": "Press barbell overhead from shoulder height."
        }
    ]

    for ex in exercises:
        exercise_ref.document(ex["id"]).set(ex)
        print(f"Seeded exercise: {ex['name']}")

    # 2. Seed Workout Sessions Collection
    sessions_ref = db.collection("workout_sessions")
    sessions = [
        {
            "id": "session_101",
            "user_id": "user_default",
            "date": "2026-09-25",
            "title": "Leg Day Heavy",
            "exercises": [
                {"exercise": "Barbell Squat", "sets": 4, "reps": 5, "weight_lbs": 225}
            ],
            "notes": "Hit a new 5-rep PR on squat!"
        },
        {
            "id": "session_102",
            "user_id": "user_default",
            "date": "2026-09-27",
            "title": "Push Day Focus",
            "exercises": [
                {"exercise": "Barbell Bench Press", "sets": 4, "reps": 8, "weight_lbs": 185},
                {"exercise": "Overhead Barbell Press", "sets": 3, "reps": 10, "weight_lbs": 115}
            ],
            "notes": "Great pump, smooth reps."
        }
    ]

    for s in sessions:
        sessions_ref.document(s["id"]).set(s)
        print(f"Seeded session: {s['title']}")

    print("Firestore seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
