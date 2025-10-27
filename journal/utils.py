<<<<<<< HEAD
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


# ============================================
# GOAL ML MODELS
# ============================================

def load_goal_models():
    """Charge les modèles ML pour goals"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return {
            'duration_model': joblib.load(os.path.join(current_dir, 'duration_model.pkl')),
            'duration_vectorizer': joblib.load(os.path.join(current_dir, 'duration_vectorizer.pkl')),
            'motivation_model': joblib.load(os.path.join(current_dir, 'motivation_model.pkl')),
            'motivation_vectorizer': joblib.load(os.path.join(current_dir, 'motivation_vectorizer.pkl')),
            'motivation_encoder': joblib.load(os.path.join(current_dir, 'motivation_label_encoder.pkl'))
        }
    except:
        return None

goal_models = load_goal_models()

MOTIVATION_MESSAGES = {
    'demarrage': [
        "🚀 Chaque grand voyage commence par un premier pas. Vous venez de le faire !", 
        "✨ L'énergie du début est magique. Profitez-en pour avancer rapidement !",
        "🌟 Excellent démarrage ! Vous avez brisé la résistance initiale !",
        "💫 Le plus dur est fait : vous avez commencé ! Continuez sur cette lancée !"
    ],
    'progression': [
        "⚡ Vous êtes en plein dans le flow ! Votre régularité paie déjà ses fruits.", 
        "🎨 Magnifique progression ! Vous construisez quelque chose de grand !",
        "🔥 Superbe momentum ! Vous avancez à un rythme idéal !",
        "📈 Votre constance est impressionnante ! Gardez ce rythme !"
    ],
    'critique': [
        "💪 C'est maintenant que les champions se révèlent. Vous êtes si proche du but !", 
        "🔥 Ne lâchez rien ! Vous êtes plus fort que ça !",
        "⚠️ Moment crucial ! Un dernier effort et la victoire est à vous !",
        "🎯 Vous touchez presque au but ! Restez concentré !"
    ],
    'sprint': [
        "🏆 C'EST PRESQUE GAGNÉ ! Sprintez jusqu'au bout !", 
        "🎉 Encore un petit effort et vous pourrez célébrer !",
        "🚀 Plus que quelques pas et c'est la ligne d'arrivée !",
        "⭐ Vous y êtes presque ! Finissez en beauté !"
    ],
    'blocage': [
        "💭 Une pause est normale. Mais recommencez AUJOURD'HUI !", 
        "⏰ Même 5 minutes valent mieux que rien !",
        "🔄 Reprenez là où vous vous êtes arrêté. Vous avez déjà bien avancé !",
        "💡 Un blocage est juste un détour vers la solution. Reprenez !"
    ],
    'completed': ["🏆 FÉLICITATIONS ! Vous l'avez fait !", "🎉 OBJECTIF ACCOMPLI !"]
}

PRACTICAL_TIPS = {
    'demarrage': [
        "💡 Astuce : Commencez par les tâches les plus faciles !",
        "💡 Conseil : Créez une routine quotidienne dès maintenant !",
        "💡 Idée : Fixez-vous un créneau horaire fixe chaque jour !"
    ],
    'progression': [
        "💡 Astuce : Maintenez votre rythme actuel !",
        "💡 Conseil : Célébrez chaque petite victoire !",
        "💡 Idée : Partagez vos progrès avec quelqu'un !"
    ],
    'critique': [
        "💡 Astuce : Visualisez-vous en train de réussir !",
        "💡 Conseil : Éliminez toutes les distractions possibles !",
        "💡 Idée : Rappelez-vous pourquoi vous avez commencé !"
    ],
    'sprint': [
        "💡 Astuce : Éliminez toutes les distractions !",
        "💡 Conseil : Donnez tout ce que vous avez !",
        "💡 Idée : Préparez votre célébration de victoire !"
    ],
    'blocage': [
        "💡 Astuce : Divisez la tâche en plus petits morceaux !",
        "💡 Conseil : Faites juste 10 minutes aujourd'hui !",
        "💡 Idée : Changez d'environnement ou d'approche !"
    ]
}


def analyze_goal_complexity(title, description, num_tasks):
    """Analyse complexité"""
    text = f"{title} {description}".lower()
    if 'maîtriser' in text or 'expert' in text or num_tasks > 15:
        return 4
    elif 'apprendre' in text or 'créer' in text or num_tasks > 8:
        return 3
    elif num_tasks > 4:
        return 2
    return 1


def predict_goal_duration(goal, user_avg_speed=None):
    """Prédit durée avec ML"""
    import pandas as pd
    import random
    
    num_tasks = len(goal.milestones) if isinstance(goal.milestones, list) else 0
    complexity = analyze_goal_complexity(goal.title, goal.description or '', num_tasks)
    
    if goal_models:
        try:
            text = f"{goal.title} {goal.description or ''}"
            text_features = goal_models['duration_vectorizer'].transform([text]).toarray()
            features = pd.DataFrame([[num_tasks, complexity]], columns=['nb_tasks', 'complexity_score'])
            text_df = pd.DataFrame(text_features)
            X = pd.concat([features.reset_index(drop=True), text_df], axis=1)
            X.columns = X.columns.astype(str)
            
            predicted_days = int(goal_models['duration_model'].predict(X)[0])
            predicted_days = max(1, min(365, predicted_days))
            margin = int(predicted_days * 0.2)
            return (predicted_days - margin, predicted_days + margin, complexity)
        except:
            pass
    
    # Fallback - retourne complexity comme int
    ranges = {1: (3, 7), 2: (7, 21), 3: (21, 60), 4: (60, 180)}
    duration_range = ranges.get(complexity, (7, 21))
    return (duration_range[0], duration_range[1], complexity)


def generate_motivation_message(goal, user):
    """Génère motivation avec ML"""
    import random
    from datetime import datetime
    import pandas as pd
    
    progress = goal.progress_pct() or 0
    num_tasks = len(goal.milestones) if isinstance(goal.milestones, list) else 0
    completed_tasks = sum(1 for m in goal.milestones if m.get('done', False)) if isinstance(goal.milestones, list) else 0
    
    phase = 'progression'
    if goal.status == 'completed':
        phase = 'completed'
    elif goal_models:
        try:
            complexity = analyze_goal_complexity(goal.title, goal.description or '', num_tasks)
            text = f"{goal.title} {goal.description or ''}"
            text_features = goal_models['motivation_vectorizer'].transform([text]).toarray()
            duration_min, duration_max, _ = predict_goal_duration(goal)
            
            features = pd.DataFrame([[num_tasks, complexity, (duration_min + duration_max) / 2]], 
                                   columns=['nb_tasks', 'complexity_score', 'actual_duration_days'])
            text_df = pd.DataFrame(text_features)
            X = pd.concat([features.reset_index(drop=True), text_df], axis=1)
            X.columns = X.columns.astype(str)
            
            prediction = goal_models['motivation_model'].predict(X)[0]
            phase = goal_models['motivation_encoder'].inverse_transform([prediction])[0]
        except:
            if progress < 20:
                phase = 'demarrage'
            elif progress < 50:
                phase = 'progression'
            elif progress < 80:
                phase = 'critique'
            else:
                phase = 'sprint'
    else:
        if progress < 20:
            phase = 'demarrage'
        elif progress < 50:
            phase = 'progression'
        elif progress < 80:
            phase = 'critique'
        else:
            phase = 'sprint'
    
    if hasattr(goal, 'updated_at') and goal.updated_at and progress < 100:
        days_since = (datetime.now().date() - goal.updated_at.date()).days
        if days_since > 5:
            phase = 'blocage'
    
    duration_min, duration_max, complexity_score = predict_goal_duration(goal)
    estimated_days_left = int((duration_min + duration_max) / 2 * (100 - progress) / 100)
    
    return {
        'message': random.choice(MOTIVATION_MESSAGES.get(phase, MOTIVATION_MESSAGES['progression'])),
        'tip': random.choice(PRACTICAL_TIPS.get(phase, PRACTICAL_TIPS['progression'])),
        'phase': phase,
        'progress': progress,
        'completed_tasks': completed_tasks,
        'remaining_tasks': num_tasks - completed_tasks,
        'estimated_days_left': estimated_days_left,
        'duration_range': f"{duration_min}-{duration_max} jours"
    }
=======
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
>>>>>>> origin/yassineJawadi
