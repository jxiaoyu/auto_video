import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]

# Google Cloud TTS uses Application Default Credentials.
# Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON path,
# or run `gcloud auth application-default login` once.

GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL = "imagen-3.0-generate-001"

VOICE_A = "en-US-Journey-F"   # female
VOICE_B = "en-US-Journey-D"   # male
LANGUAGE_CODE = "en-US"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

OUTPUT_DIR = "output"
