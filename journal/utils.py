import re 
import string
import joblib
import numpy as np
import os


def clean_text(text):
    """Clean and process text data"""
    text = str(text).lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)  # Remove URLs
    text = re.sub(r'@\w+', '', text)  # Remove mentions
    text = re.sub(r'#\w+', '', text)  # Remove hashtags
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\d+', '', text)  # Remove numbers
    text = re.sub(r'\s+', ' ', text).strip()  # Remove extra spaces
    return text

# Define emotion labels (adjust based on your dataset)
emotion_labels = {0: 'sadness', 1: 'joy', 2: 'love', 3: 'anger', 4: 'fear', 5: 'surprise'}

def predict_emotion(text, model=None):
    """Predict emotion for custom text"""
    # Clean the text
    cleaned = clean_text(text)
    if model == None:
        return None, 0.0
    
    # Predict emotion using cleaned text
    prediction = model.predict([cleaned])[0]
    prediction_proba = model.predict_proba([cleaned])[0]
    
    # Get emotion label and confidence
    emotion = emotion_labels.get(prediction, 'unknown')
    confidence = np.max(prediction_proba)
    
    return emotion, confidence

# Load the model using absolute path
def load_model():
    """Load the emotion prediction model"""
    try:
        # Get the directory of the current file (journal app)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, 'lr_model.pkl')
        return joblib.load(model_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        return None

lr_model = load_model()