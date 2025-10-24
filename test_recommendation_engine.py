#!/usr/bin/env python3
"""
Script de test pour le moteur de recommandations amélioré
"""

import sys
import os
import json
from datetime import datetime

# Ajouter le répertoire journal au path pour importer le module
sys.path.append(os.path.join(os.path.dirname(__file__), 'journal'))

try:
    from recommendation_engine import ActivityRecommendationEngine
    print("✅ Import du moteur de recommandations réussi")
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)

def test_engine_initialization():
    """Test l'initialisation du moteur"""
    print("\n🔧 Test d'initialisation du moteur...")
    
    try:
        engine = ActivityRecommendationEngine()
        print("✅ Moteur initialisé avec succès")
        
        # Vérifier les statistiques
        stats = engine.get_stats()
        print(f"📊 Statistiques: {stats['total_emotions']} émotions, {stats['total_activities']} activités")
        print(f"📂 Source des données: {stats['data_source']}")
        print(f"📋 Émotions disponibles: {', '.join(stats['emotions'])}")
        
        return engine
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        return None

def test_basic_recommendations(engine):
    """Test les recommandations de base"""
    print("\n🎯 Test des recommandations de base...")
    
    emotions_to_test = ['joy', 'sadness', 'love', 'anger', 'fear', 'surprise']
    
    for emotion in emotions_to_test:
        try:
            recommendations = engine.get_recommendations(emotion, confidence=0.8)
            print(f"✅ {emotion}: {len(recommendations['activities'])} activités générées")
            print(f"   Couleur: {recommendations['color']}, Icône: {recommendations['icon']}")
            print(f"   Encouragement: {recommendations['encouragement'][:50]}...")
        except Exception as e:
            print(f"❌ Erreur pour {emotion}: {e}")

def test_contextual_recommendations(engine):
    """Test les recommandations contextuelles"""
    print("\n🌍 Test des recommandations contextuelles...")
    
    contexts = [
        {'time_of_day': 'morning', 'weather': 'sunny'},
        {'time_of_day': 'evening', 'weather': 'rainy', 'user_name': 'Alice'},
        {'time_of_day': 'afternoon'}
    ]
    
    for i, context in enumerate(contexts, 1):
        try:
            recommendations = engine.get_recommendations('joy', confidence=0.9, context=context)
            print(f"✅ Contexte {i}: {len(recommendations['activities'])} activités personnalisées")
            print(f"   Contexte appliqué: {recommendations['context_applied']}")
            print(f"   Exemple d'activité: {recommendations['activities'][0]}")
        except Exception as e:
            print(f"❌ Erreur pour le contexte {i}: {e}")

def test_emotion_mapping(engine):
    """Test le mapping des émotions similaires"""
    print("\n🔄 Test du mapping des émotions...")
    
    similar_emotions = ['happy', 'sad', 'angry', 'scared', 'amazed', 'excited']
    
    for emotion in similar_emotions:
        try:
            recommendations = engine.get_recommendations(emotion, confidence=0.7)
            mapped_emotion = recommendations['emotion']
            print(f"✅ '{emotion}' → '{mapped_emotion}': {len(recommendations['activities'])} activités")
        except Exception as e:
            print(f"❌ Erreur pour {emotion}: {e}")

def test_confidence_levels(engine):
    """Test les différents niveaux de confiance"""
    print("\n📈 Test des niveaux de confiance...")
    
    confidence_levels = [0.2, 0.5, 0.7, 0.9]
    
    for confidence in confidence_levels:
        try:
            recommendations = engine.get_recommendations('joy', confidence=confidence)
            num_activities = len(recommendations['activities'])
            print(f"✅ Confiance {confidence}: {num_activities} activités générées")
        except Exception as e:
            print(f"❌ Erreur pour confiance {confidence}: {e}")

def test_emotion_info(engine):
    """Test les informations détaillées sur les émotions"""
    print("\n📋 Test des informations sur les émotions...")
    
    emotions_to_check = ['joy', 'nonexistent_emotion', 'happy']
    
    for emotion in emotions_to_check:
        try:
            info = engine.get_emotion_info(emotion)
            if info['found']:
                print(f"✅ {emotion}: {info['activities_count']} activités, {info['encouragement_messages_count']} messages")
            else:
                similar = info.get('similar_emotion', 'Aucune')
                print(f"⚠️ {emotion}: Non trouvée, similaire: {similar}")
        except Exception as e:
            print(f"❌ Erreur pour {emotion}: {e}")

def test_reload_functionality(engine):
    """Test la fonctionnalité de rechargement"""
    print("\n🔄 Test du rechargement des données...")
    
    try:
        success = engine.reload_recommendations()
        if success:
            print("✅ Rechargement des données réussi")
        else:
            print("⚠️ Rechargement échoué mais géré")
    except Exception as e:
        print(f"❌ Erreur lors du rechargement: {e}")

def main():
    """Fonction principale de test"""
    print("🚀 Démarrage des tests du moteur de recommandations amélioré")
    print("=" * 60)
    
    # Test d'initialisation
    engine = test_engine_initialization()
    if not engine:
        print("❌ Impossible de continuer les tests sans moteur initialisé")
        return
    
    # Tests fonctionnels
    test_basic_recommendations(engine)
    test_contextual_recommendations(engine)
    test_emotion_mapping(engine)
    test_confidence_levels(engine)
    test_emotion_info(engine)
    test_reload_functionality(engine)
    
    print("\n" + "=" * 60)
    print("🎉 Tests terminés ! Vérifiez les résultats ci-dessus.")
    
    # Afficher un exemple complet
    print("\n📝 Exemple de recommandation complète:")
    try:
        example = engine.get_recommendations(
            'sadness', 
            confidence=0.85, 
            context={'time_of_day': 'evening', 'user_name': 'Utilisateur'}
        )
        print(json.dumps(example, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Erreur lors de l'exemple: {e}")

if __name__ == "__main__":
    main()