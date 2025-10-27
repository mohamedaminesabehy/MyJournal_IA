"""
Configuration des services IA
"""
import os
from pathlib import Path

# Chemins de base
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Configuration Google Vision API
GOOGLE_VISION_API_KEY = os.getenv('GOOGLE_VISION_API_KEY', '')
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')

# Configuration OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Configuration Google Gemini
GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY', '')

# Configuration Hugging Face
HUGGING_FACE_API_KEY = os.getenv('HUGGING_FACE_API_KEY', '')

# Services à utiliser
AI_VISION_SERVICE = os.getenv('AI_VISION_SERVICE', 'google_vision')  # google_vision, clip, gpt4_vision
AI_GENERATIVE_SERVICE = os.getenv('AI_GENERATIVE_SERVICE', 'gpt4')  # gpt4, gemini, claude

# Paramètres d'analyse
AUTO_ANALYZE_ON_UPLOAD = os.getenv('AUTO_ANALYZE_ON_UPLOAD', 'True') == 'True'
VISION_CONFIDENCE_THRESHOLD = float(os.getenv('VISION_CONFIDENCE_THRESHOLD', '0.7'))
MAX_TAGS_PER_MEDIA = int(os.getenv('MAX_TAGS_PER_MEDIA', '10'))

# Langues supportées
SUPPORTED_LANGUAGES = ['fr', 'en', 'es', 'de']
DEFAULT_LANGUAGE = 'fr'

# Paramètres de détection
FACE_DETECTION_ENABLED = True
TEXT_DETECTION_ENABLED = True
LOCATION_DETECTION_ENABLED = True
COLOR_ANALYSIS_ENABLED = True
EMOTION_DETECTION_ENABLED = True

# Paramètres de génération
GENERATE_CREATIVE_TITLES = True
GENERATE_POETIC_DESCRIPTIONS = True
SUGGEST_FILTERS = True
SUGGEST_TAGS = True

# Cache et performance
ENABLE_CACHE = True
CACHE_TIMEOUT = 3600  # 1 heure en secondes
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB pour l'analyse
THUMBNAIL_SIZE = (300, 300)

# Limites
MAX_CONCURRENT_ANALYSIS = 5
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
