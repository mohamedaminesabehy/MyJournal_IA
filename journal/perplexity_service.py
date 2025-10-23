import requests
import json
import logging
from typing import Dict, List, Optional
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class PerplexityEnrichmentService:
    """
    Service pour enrichir les recommandations d'activités avec du contenu contextuel
    via l'API Perplexity.ai
    """
    
    def __init__(self):
        self.api_key = "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"
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def enrich_recommendations(self, recommendations: List[str], emotion: str, note_content: str = "") -> Dict:
        """
        Enrichit les recommandations d'activités avec du contenu multimédia contextuel
        
        Args:
            recommendations: Liste des recommandations d'activités
            emotion: Émotion détectée (joie, tristesse, colère, etc.)
            note_content: Contenu de la note pour plus de contexte
            
        Returns:
            Dict contenant le contenu enrichi organisé par catégories
        """
        try:
            prompt = self._build_enrichment_prompt(recommendations, emotion, note_content)
            
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "system",
                        "content": "Tu es un assistant spécialisé dans le bien-être qui enrichit les recommandations d'activités avec du contenu multimédia pertinent et des explications scientifiques courtes."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.7,
                "search_domain_filter": ["youtube.com", "spotify.com", "psychology.org", "healthline.com"],
                "return_citations": True
            }
            
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_enrichment_response(result)
            else:
                print(f"Erreur API Perplexity: {response.status_code} - {response.text}")
                return self._get_fallback_enrichment(recommendations, emotion)
                
        except Exception as e:
            print(f"Erreur lors de l'enrichissement Perplexity: {str(e)}")
            return self._get_fallback_enrichment(recommendations, emotion)
    
    def _build_enrichment_prompt(self, recommendations: List[str], emotion: str, note_content: str) -> str:
        """Construit le prompt pour l'API Perplexity"""
        
        recommendations_text = ", ".join(recommendations)
        
        prompt = f"""
        Basé sur ces recommandations d'activités: {recommendations_text}
        Pour une personne ressentant: {emotion}
        
        Fournis un enrichissement structuré en JSON avec exactement cette structure:
        {{
            "explanation": "Explication scientifique courte (2-3 phrases) sur pourquoi ces activités aident avec {emotion}",
            "multimedia_content": {{
                "music": {{
                    "title": "Titre de la recommandation musicale",
                    "description": "Description courte",
                    "links": ["lien1", "lien2"]
                }},
                "videos": {{
                    "title": "Titre de la recommandation vidéo",
                    "description": "Description courte", 
                    "links": ["lien1", "lien2"]
                }},
                "resources": {{
                    "title": "Titre des ressources additionnelles",
                    "description": "Description courte",
                    "links": ["lien1", "lien2"]
                }}
            }},
            "local_suggestions": {{
                "title": "Suggestions d'activités locales",
                "description": "Types de lieux ou activités à rechercher localement",
                "keywords": ["mot-clé1", "mot-clé2", "mot-clé3"]
            }}
        }}
        
        Assure-toi que les liens sont réels et fonctionnels. Concentre-toi sur du contenu de qualité adapté à l'émotion {emotion}.
        """
        
        return prompt
    
    def _parse_enrichment_response(self, response: Dict) -> Dict:
        """Parse la réponse de l'API Perplexity"""
        try:
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # Extraire le JSON de la réponse
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_content = content[start_idx:end_idx]
                enrichment_data = json.loads(json_content)
                
                # Ajouter les citations si disponibles
                citations = response.get('citations', [])
                if citations:
                    enrichment_data['citations'] = citations
                
                return enrichment_data
            else:
                return self._get_default_enrichment()
                
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Erreur lors du parsing de la réponse Perplexity: {str(e)}")
            return self._get_default_enrichment()
    
    def _get_fallback_enrichment(self, recommendations: List[str], emotion: str) -> Dict:
        """Contenu de fallback en cas d'erreur API"""
        
        emotion_explanations = {
            'joy': "La joie stimule la production de dopamine et sérotonine, renforçant les connexions sociales et la créativité.",
            'sadness': "La tristesse permet le traitement émotionnel et la réflexion. Ces activités aident à réguler l'humeur naturellement.",
            'anger': "La colère active le système sympathique. Ces activités aident à canaliser l'énergie et retrouver l'équilibre.",
            'fear': "La peur déclenche des réponses de stress. Ces activités favorisent la relaxation et le sentiment de sécurité.",
            'love': "L'amour libère de l'ocytocine, renforçant les liens sociaux et le bien-être général.",
            'surprise': "La surprise stimule l'attention et l'apprentissage. Ces activités aident à intégrer les nouvelles expériences."
        }
        
        return {
            "explanation": emotion_explanations.get(emotion, "Ces activités sont bénéfiques pour votre bien-être émotionnel."),
            "multimedia_content": {
                "music": {
                    "title": "Musique apaisante recommandée",
                    "description": "Playlists adaptées à votre état émotionnel",
                    "links": ["https://open.spotify.com/playlist/37i9dQZF1DWXe9gFZP0gtP"]
                },
                "videos": {
                    "title": "Vidéos de bien-être",
                    "description": "Contenu vidéo pour améliorer votre humeur",
                    "links": ["https://www.youtube.com/results?search_query=meditation+relaxation"]
                },
                "resources": {
                    "title": "Ressources de bien-être",
                    "description": "Articles et guides sur la gestion émotionnelle",
                    "links": ["https://www.psychologytoday.com/us/basics/emotion"]
                }
            },
            "local_suggestions": {
                "title": "Activités locales suggérées",
                "description": "Recherchez ces types d'activités près de chez vous",
                "keywords": ["parc", "café", "bibliothèque", "centre de bien-être"]
            }
        }
    
    def _get_default_enrichment(self) -> Dict:
        """Contenu par défaut minimal"""
        return {
            "explanation": "Ces activités sont conçues pour améliorer votre bien-être émotionnel.",
            "multimedia_content": {
                "music": {
                    "title": "Contenu musical personnalisé",
                    "description": "Découvrez de la musique adaptée à votre humeur",
                    "links": []
                },
                "videos": {
                    "title": "Vidéos inspirantes",
                    "description": "Contenu vidéo pour votre bien-être",
                    "links": []
                },
                "resources": {
                    "title": "Ressources utiles",
                    "description": "Guides et articles sur le bien-être",
                    "links": []
                }
            },
            "local_suggestions": {
                "title": "Explorez votre environnement",
                "description": "Trouvez des activités près de chez vous",
                "keywords": ["nature", "culture", "sport", "détente"]
            }
        }

# Instance globale du service
perplexity_service = PerplexityEnrichmentService()