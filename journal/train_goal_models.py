"""
Script pour entraîner les modèles ML de prédiction de durée et motivation des objectifs
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
import os

# Charger le dataset
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, 'goals_training_dataset.csv')
data = pd.read_csv(data_path)

print(f"Dataset chargé : {len(data)} exemples")
print(f"Colonnes : {list(data.columns)}")

# ============================================
# MODÈLE 1 : Prédiction de durée
# ============================================

print("\n=== Entraînement du modèle de prédiction de durée ===")

# Feature engineering pour la durée
X_duration = data[['nb_tasks', 'complexity_score']].copy()

# Ajouter des features textuelles
vectorizer_duration = TfidfVectorizer(max_features=50)
text_features = vectorizer_duration.fit_transform(data['title'] + ' ' + data['description'])
text_features_dense = pd.DataFrame(text_features.toarray())

# Combiner les features
X_duration_combined = pd.concat([X_duration.reset_index(drop=True), text_features_dense], axis=1)
X_duration_combined.columns = X_duration_combined.columns.astype(str)

y_duration = data['actual_duration_days']

# Split
X_train_dur, X_test_dur, y_train_dur, y_test_dur = train_test_split(
    X_duration_combined, y_duration, test_size=0.2, random_state=42
)

# Entraîner le modèle
duration_model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
duration_model.fit(X_train_dur, y_train_dur)

# Évaluer
score_dur = duration_model.score(X_test_dur, y_test_dur)
print(f"Score R² du modèle de durée : {score_dur:.3f}")

# Sauvegarder
duration_model_path = os.path.join(script_dir, 'duration_model.pkl')
vectorizer_duration_path = os.path.join(script_dir, 'duration_vectorizer.pkl')
joblib.dump(duration_model, duration_model_path)
joblib.dump(vectorizer_duration, vectorizer_duration_path)
print(f"✅ Modèle de durée sauvegardé : {duration_model_path}")

# ============================================
# MODÈLE 2 : Classification de motivation
# ============================================

print("\n=== Entraînement du modèle de motivation ===")

# Feature engineering pour la motivation
X_motivation = data[['nb_tasks', 'complexity_score', 'actual_duration_days']].copy()

# Ajouter des features textuelles
vectorizer_motivation = TfidfVectorizer(max_features=50)
text_features_mot = vectorizer_motivation.fit_transform(data['title'] + ' ' + data['description'])
text_features_mot_dense = pd.DataFrame(text_features_mot.toarray())

# Combiner les features
X_motivation_combined = pd.concat([X_motivation.reset_index(drop=True), text_features_mot_dense], axis=1)
X_motivation_combined.columns = X_motivation_combined.columns.astype(str)

# Encoder les labels
label_encoder = LabelEncoder()
y_motivation = label_encoder.fit_transform(data['motivation_phase'])

print(f"Classes de motivation : {list(label_encoder.classes_)}")

# Split
X_train_mot, X_test_mot, y_train_mot, y_test_mot = train_test_split(
    X_motivation_combined, y_motivation, test_size=0.2, random_state=42
)

# Entraîner le modèle
motivation_model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
motivation_model.fit(X_train_mot, y_train_mot)

# Évaluer
score_mot = motivation_model.score(X_test_mot, y_test_mot)
print(f"Score accuracy du modèle de motivation : {score_mot:.3f}")

# Sauvegarder
motivation_model_path = os.path.join(script_dir, 'motivation_model.pkl')
vectorizer_motivation_path = os.path.join(script_dir, 'motivation_vectorizer.pkl')
label_encoder_path = os.path.join(script_dir, 'motivation_label_encoder.pkl')
joblib.dump(motivation_model, motivation_model_path)
joblib.dump(vectorizer_motivation, vectorizer_motivation_path)
joblib.dump(label_encoder, label_encoder_path)
print(f"✅ Modèle de motivation sauvegardé : {motivation_model_path}")

print("\n🎉 Entraînement terminé avec succès !")
print(f"\nFichiers créés :")
print(f"  - {duration_model_path}")
print(f"  - {duration_vectorizer_path}")
print(f"  - {motivation_model_path}")
print(f"  - {motivation_vectorizer_path}")
print(f"  - {label_encoder_path}")
