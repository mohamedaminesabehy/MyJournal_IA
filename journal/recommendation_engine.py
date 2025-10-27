import random
import json
import os
from typing import List, Dict, Tuple
from datetime import datetime


class ActivityRecommendationEngine:
    """
    Moteur de recommandations d'activités basé sur l'analyse d'émotions
    Utilise un fichier JSON externe pour les données de recommandations
    """
    
    def __init__(self, json_file_path: str = None):
        # Chemin vers le fichier JSON des recommandations
        if json_file_path is None:
            # Chemin par défaut relatif au fichier actuel
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_file_path = os.path.join(current_dir, '..', 'dataset', 'recommandations.json')
        
        self.json_file_path = json_file_path
        self.recommendations_db = self._load_recommendations()
        
        # Fallback data en cas d'échec du chargement (données minimales)
        self._fallback_db = {
            'joy': {
                'activities': ["Profite de ce moment de bonheur"],
                'color': '#f59e0b',
                'icon': 'fas fa-smile',
                'encouragement_messages': ["Continue à cultiver cette joie !"]
            },
            'sadness': {
                'activities': ["Prends soin de toi avec douceur"],
                'color': '#6366f1',
                'icon': 'fas fa-heart',
                'encouragement_messages': ["Ces moments difficiles passeront."]
            }
        }
        
        # Recommandations contextuelles basées sur l'heure
        self.time_based_modifiers = {
            'morning': ['Commence ta journée par', 'Ce matin, essaie de', 'Pour bien démarrer'],
            'afternoon': ['Cet après-midi, pourquoi ne pas', 'Pour cette pause', 'En milieu de journée'],
            'evening': ['Ce soir, tu pourrais', 'Pour terminer la journée', 'En soirée']
        }
        
        # Recommandations basées sur la météo (simulation)
        self.weather_modifiers = {
            'sunny': ['Profite du beau temps pour', 'Avec ce soleil'],
            'rainy': ['Malgré la pluie', 'Par ce temps pluvieux'],
            'cloudy': ['Même par temps nuageux', 'Profite de cette journée']
        }

    def _load_recommendations(self) -> Dict:
        """
        Charge les recommandations depuis le fichier JSON
        
        Returns:
            Dict: Les données de recommandations ou fallback en cas d'erreur
        """
        try:
            if not os.path.exists(self.json_file_path):
                print(f"Attention: Fichier {self.json_file_path} non trouvé. Utilisation des données de fallback.")
                return self._fallback_db
            
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
            # Validation des données chargées
            if not isinstance(data, dict):
                raise ValueError("Le fichier JSON doit contenir un dictionnaire")
                
            # Vérifier que chaque émotion a les champs requis
            for emotion, emotion_data in data.items():
                required_fields = ['activities', 'color', 'icon']
                for field in required_fields:
                    if field not in emotion_data:
                        raise ValueError(f"Champ manquant '{field}' pour l'émotion '{emotion}'")
                        
                if not isinstance(emotion_data['activities'], list) or len(emotion_data['activities']) == 0:
                    raise ValueError(f"Les activités pour '{emotion}' doivent être une liste non vide")
            
            print(f"Données de recommandations chargées avec succès depuis {self.json_file_path}")
            print(f"Émotions disponibles: {list(data.keys())}")
            return data
            
        except FileNotFoundError:
            print(f"Erreur: Fichier {self.json_file_path} non trouvé. Utilisation des données de fallback.")
            return self._fallback_db
        except json.JSONDecodeError as e:
            print(f"Erreur de format JSON dans {self.json_file_path}: {e}. Utilisation des données de fallback.")
            return self._fallback_db
        except Exception as e:
            print(f"Erreur lors du chargement de {self.json_file_path}: {e}. Utilisation des données de fallback.")
            return self._fallback_db

    def reload_recommendations(self) -> bool:
        """
        Recharge les recommandations depuis le fichier JSON
        
        Returns:
            bool: True si le rechargement a réussi, False sinon
        """
        try:
            new_data = self._load_recommendations()
            self.recommendations_db = new_data
            return True
        except Exception as e:
            print(f"Erreur lors du rechargement: {e}")
            return False

    def get_recommendations(self, emotion: str, confidence: float = 0.0, 
                          context: Dict = None) -> Dict:
        """
        Génère des recommandations personnalisées basées sur l'émotion
        
        Args:
            emotion: L'émotion détectée
            confidence: Le niveau de confiance de la prédiction (0.0 à 1.0)
            context: Contexte additionnel (heure, météo, historique, etc.)
            
        Returns:
            Dict contenant les recommandations et métadonnées
        """
        # Normaliser l'émotion et gérer les cas non supportés
        emotion = emotion.lower().strip() if emotion else 'joy'
        
        if emotion not in self.recommendations_db:
            # Essayer de trouver une émotion similaire ou utiliser joy par défaut
            available_emotions = list(self.recommendations_db.keys())
            emotion = self._find_similar_emotion(emotion, available_emotions) or 'joy'
            
        emotion_data = self.recommendations_db.get(emotion, self.recommendations_db.get('joy', self._fallback_db['joy']))
        
        # Logique améliorée pour le nombre de recommandations basée sur la confiance
        base_recommendations = 3
        if confidence > 0.8:
            num_recommendations = 5  # Haute confiance = plus de suggestions
        elif confidence > 0.6:
            num_recommendations = 4
        else:
            num_recommendations = base_recommendations
            
        # Sélectionner les recommandations avec une logique intelligente
        selected_activities = self._select_smart_activities(
            emotion_data['activities'], 
            num_recommendations, 
            context
        )
        
        # Personnaliser les recommandations avec le contexte
        personalized_activities = []
        for activity in selected_activities:
            personalized_activity = self._personalize_activity(activity, context, emotion)
            personalized_activities.append(personalized_activity)
        
        # Générer un message d'encouragement personnalisé
        encouragement = self._generate_encouragement(emotion, confidence, context)
        
        # Ajouter des métadonnées enrichies
        result = {
            'emotion': emotion,
            'confidence': confidence,
            'activities': personalized_activities,
            'encouragement': encouragement,
            'color': emotion_data.get('color', '#6366f1'),
            'icon': emotion_data.get('icon', 'fas fa-heart'),
            'emotion_display': self._get_emotion_display(emotion),
            'timestamp': datetime.now().isoformat(),
            'context_applied': bool(context),
            'total_available_activities': len(emotion_data['activities'])
        }
        
        return result

    def _find_similar_emotion(self, emotion: str, available_emotions: List[str]) -> str:
        """
        Trouve une émotion similaire dans la base de données
        
        Args:
            emotion: L'émotion recherchée
            available_emotions: Liste des émotions disponibles
            
        Returns:
            str: Émotion similaire trouvée ou None
        """
        # Mapping des émotions similaires
        emotion_mapping = {
            'happy': 'joy',
            'happiness': 'joy',
            'glad': 'joy',
            'excited': 'joy',
            'sad': 'sadness',
            'depressed': 'sadness',
            'melancholy': 'sadness',
            'angry': 'anger',
            'mad': 'anger',
            'furious': 'anger',
            'rage': 'anger',
            'scared': 'fear',
            'afraid': 'fear',
            'anxious': 'fear',
            'worried': 'fear',
            'amazed': 'surprise',
            'astonished': 'surprise',
            'shocked': 'surprise',
            'affection': 'love',
            'adoration': 'love',
            'romance': 'love'
        }
        
        return emotion_mapping.get(emotion.lower())

    def _select_smart_activities(self, activities: List[str], num_recommendations: int, context: Dict = None) -> List[str]:
        """
        Sélectionne intelligemment les activités basées sur le contexte
        
        Args:
            activities: Liste des activités disponibles
            num_recommendations: Nombre de recommandations à retourner
            context: Contexte pour la sélection
            
        Returns:
            List[str]: Activités sélectionnées
        """
        if not activities:
            return []
            
        available_activities = activities.copy()
        num_recommendations = min(num_recommendations, len(available_activities))
        
        # Si pas de contexte, sélection aléatoire
        if not context:
            return random.sample(available_activities, num_recommendations)
        
        # Logique de sélection contextuelle
        selected = []
        
        # Priorité basée sur l'heure de la journée
        if 'time_of_day' in context:
            time_keywords = {
                'morning': ['commence', 'matin', 'démarrer', 'réveil'],
                'afternoon': ['pause', 'milieu', 'après-midi'],
                'evening': ['soir', 'terminer', 'relaxant', 'calme']
            }
            
            time_of_day = context['time_of_day']
            if time_of_day in time_keywords:
                keywords = time_keywords[time_of_day]
                
                # Chercher des activités qui correspondent à l'heure
                for activity in available_activities[:]:
                    if any(keyword in activity.lower() for keyword in keywords):
                        selected.append(activity)
                        available_activities.remove(activity)
                        if len(selected) >= num_recommendations:
                            break
        
        # Compléter avec des sélections aléatoires si nécessaire
        remaining_needed = num_recommendations - len(selected)
        if remaining_needed > 0 and available_activities:
            remaining_selected = random.sample(
                available_activities, 
                min(remaining_needed, len(available_activities))
            )
            selected.extend(remaining_selected)
        
        return selected[:num_recommendations]
    
    def _personalize_activity(self, activity: str, context: Dict = None, emotion: str = None) -> str:
        """
        Personnalise une activité avec le contexte et l'émotion
        
        Args:
            activity: L'activité de base
            context: Contexte additionnel
            emotion: L'émotion actuelle
            
        Returns:
            str: Activité personnalisée
        """
        if not context:
            return activity
            
        personalized = activity
        
        # Ajouter des modificateurs temporels
        if 'time_of_day' in context:
            time_modifiers = self.time_based_modifiers.get(context['time_of_day'], [])
            if time_modifiers and random.random() < 0.4:  # 40% de chance
                modifier = random.choice(time_modifiers)
                personalized = f"{modifier} {activity.lower()}"
        
        # Ajouter des modificateurs météo
        if 'weather' in context:
            weather_modifiers = self.weather_modifiers.get(context['weather'], [])
            if weather_modifiers and random.random() < 0.3:  # 30% de chance
                modifier = random.choice(weather_modifiers)
                personalized = f"{modifier} {activity.lower()}"
        
        # Ajouter le nom de l'utilisateur si disponible
        if 'user_name' in context and random.random() < 0.2:  # 20% de chance
            personalized = f"{context['user_name']}, {personalized.lower()}"
        
        return personalized
    
    def _generate_encouragement(self, emotion: str, confidence: float, context: Dict = None) -> str:
        """
        Génère un message d'encouragement personnalisé et contextuel
        
        Args:
            emotion: L'émotion détectée
            confidence: Niveau de confiance
            context: Contexte additionnel
            
        Returns:
            str: Message d'encouragement personnalisé
        """
        # Utiliser les messages du fichier JSON si disponibles
        emotion_data = self.recommendations_db.get(emotion, {})
        if 'encouragement_messages' in emotion_data and emotion_data['encouragement_messages']:
            base_messages = emotion_data['encouragement_messages']
        else:
            # Messages de fallback par émotion
            base_messages = self._get_fallback_encouragements(emotion)
        
        # Sélectionner un message de base
        base_message = random.choice(base_messages)
        
        # Personnaliser selon la confiance
        if confidence > 0.8:
            confidence_modifier = " Je suis très confiant dans cette analyse."
        elif confidence > 0.6:
            confidence_modifier = " Cette analyse semble fiable."
        elif confidence > 0.3:
            confidence_modifier = " Voici ce que je perçois de ton état émotionnel."
        else:
            confidence_modifier = " Ces suggestions peuvent t'aider peu importe ton état actuel."
        
        # Ajouter le contexte temporel si disponible
        time_context = ""
        if context and 'time_of_day' in context:
            time_phrases = {
                'morning': " Pour bien commencer cette journée,",
                'afternoon': " En cette mi-journée,",
                'evening': " Pour terminer cette journée en beauté,"
            }
            time_context = time_phrases.get(context['time_of_day'], "")
        
        # Construire le message final
        final_message = f"{base_message}{confidence_modifier}{time_context}"
        
        return final_message.strip()
    
    def _get_fallback_encouragements(self, emotion: str) -> List[str]:
        """
        Retourne des messages d'encouragement de fallback pour une émotion
        
        Args:
            emotion: L'émotion
            
        Returns:
            List[str]: Liste des messages d'encouragement
        """
        fallback_encouragements = {
            'sadness': [
                "Il est normal de se sentir triste parfois. Ces activités peuvent t'aider à retrouver un peu de sérénité.",
                "Prends soin de toi, tu mérites de la douceur et de la bienveillance.",
                "Ces moments difficiles passeront. En attendant, voici quelques idées pour te réconforter."
            ],
            'joy': [
                "Quelle belle énergie ! Profite de ce moment de bonheur et amplifie-le avec ces activités.",
                "Ta joie est contagieuse ! Voici comment la cultiver et la partager.",
                "C'est merveilleux de te sentir si bien ! Continue sur cette lancée positive."
            ],
            'love': [
                "L'amour que tu ressens est précieux. Voici comment le célébrer et le nourrir.",
                "Ces sentiments d'amour méritent d'être chéris. Laisse-toi inspirer par ces suggestions.",
                "Quel bonheur de ressentir tant d'amour ! Voici comment l'exprimer pleinement."
            ],
            'anger': [
                "La colère est une émotion valide. Voici des moyens sains de la canaliser.",
                "Il est important d'exprimer ta colère de manière constructive. Ces activités peuvent t'aider.",
                "Transforme cette énergie en quelque chose de positif avec ces suggestions."
            ],
            'fear': [
                "Il est courageux de reconnaître ses peurs. Voici des moyens de les apprivoiser.",
                "Tu n'es pas seul(e) face à tes inquiétudes. Ces activités peuvent t'apporter du réconfort.",
                "Chaque petit pas compte pour surmonter ses peurs. Commence par ces suggestions."
            ],
            'surprise': [
                "Les surprises rendent la vie plus riche ! Voici comment explorer cette découverte.",
                "Quelle belle surprise ! Laisse-toi porter par cette émotion avec ces activités.",
                "L'inattendu peut être merveilleux. Voici comment en tirer le meilleur parti."
            ]
        }
        
        return fallback_encouragements.get(emotion, fallback_encouragements['joy'])
    
    def _get_emotion_display(self, emotion: str) -> str:
        """Retourne le nom d'affichage de l'émotion en français"""
        emotions_fr = {
            'joy': 'Joie',
            'sadness': 'Tristesse',
            'love': 'Amour',
            'anger': 'Colère',
            'fear': 'Peur',
            'surprise': 'Surprise'
        }
        return emotions_fr.get(emotion, 'Neutre')
    
    def get_activity_categories(self) -> List[str]:
        """Retourne la liste des catégories d'activités disponibles"""
        return list(self.recommendations_db.keys())
    
    def get_stats(self) -> Dict:
        """Retourne des statistiques détaillées sur la base de recommandations"""
        if not self.recommendations_db:
            return {
                'total_emotions': 0,
                'total_activities': 0,
                'emotions': [],
                'status': 'No data loaded'
            }
            
        total_activities = sum(len(data.get('activities', [])) for data in self.recommendations_db.values())
        
        # Statistiques détaillées par émotion
        emotion_stats = {}
        for emotion, data in self.recommendations_db.items():
            emotion_stats[emotion] = {
                'activities_count': len(data.get('activities', [])),
                'has_encouragement_messages': 'encouragement_messages' in data,
                'encouragement_count': len(data.get('encouragement_messages', [])),
                'color': data.get('color', 'N/A'),
                'icon': data.get('icon', 'N/A')
            }
        
        return {
            'total_emotions': len(self.recommendations_db),
            'total_activities': total_activities,
            'emotions': list(self.recommendations_db.keys()),
            'emotion_details': emotion_stats,
            'data_source': self.json_file_path,
            'last_loaded': datetime.now().isoformat(),
            'status': 'Data loaded successfully'
        }

    def get_emotion_info(self, emotion: str) -> Dict:
        """
        Retourne des informations détaillées sur une émotion spécifique
        
        Args:
            emotion: L'émotion à analyser
            
        Returns:
            Dict: Informations sur l'émotion
        """
        emotion = emotion.lower().strip()
        
        if emotion not in self.recommendations_db:
            similar = self._find_similar_emotion(emotion, list(self.recommendations_db.keys()))
            return {
                'emotion': emotion,
                'found': False,
                'similar_emotion': similar,
                'available_emotions': list(self.recommendations_db.keys())
            }
        
        emotion_data = self.recommendations_db[emotion]
        
        return {
            'emotion': emotion,
            'found': True,
            'display_name': self._get_emotion_display(emotion),
            'activities_count': len(emotion_data.get('activities', [])),
            'sample_activities': emotion_data.get('activities', [])[:3],  # 3 premiers exemples
            'encouragement_messages_count': len(emotion_data.get('encouragement_messages', [])),
            'color': emotion_data.get('color'),
            'icon': emotion_data.get('icon'),
            'has_custom_encouragements': 'encouragement_messages' in emotion_data
        }


# Instance globale du moteur de recommandations
recommendation_engine = ActivityRecommendationEngine()