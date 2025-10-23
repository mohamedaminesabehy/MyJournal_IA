"""
Module pour améliorer la qualité des titres et descriptions générés par l'IA
"""
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class DescriptionEnhancer:
    """Classe pour améliorer les titres et descriptions d'images"""
    
    def __init__(self):
        self.object_translations = {
            'photo': 'photographie',
            'image': 'image numérique',
            'nature': 'paysage naturel',
            'sky': 'ciel',
            'colorful scene': 'scène colorée',
            'person': 'portrait',
            'people': 'groupe de personnes',
            'building': 'architecture',
            'food': 'gastronomie',
            'animal': 'faune',
            'flower': 'flore',
            'car': 'véhicule',
            'sunset': 'coucher de soleil',
            'beach': 'plage',
            'mountain': 'montagne',
            'forest': 'forêt',
            'city': 'paysage urbain',
        }
        
        self.emotion_descriptions = {
            'joyeuse': 'une atmosphère joyeuse et vivante',
            'paisible': 'une ambiance calme et sereine',
            'dramatique': 'une composition dramatique et intense',
            'mélancolique': 'une émotion mélancolique et contemplative',
            'énergique': 'une énergie dynamique et vibrante',
            'romantique': 'une atmosphère romantique et douce',
        }
    
    def generate_smart_title(self, analysis_results: Dict) -> str:
        """
        Génère un titre intelligent et significatif
        
        Args:
            analysis_results: Résultats complets de l'analyse Vision AI
            
        Returns:
            Titre créatif et descriptif
        """
        objects = [obj['object'] for obj in analysis_results.get('detected_objects', [])]
        emotions = [emo['emotion'] for emo in analysis_results.get('detected_emotions', [])]
        locations = analysis_results.get('detected_locations', [])
        colors = analysis_results.get('dominant_colors', [])
        
        # Filtrer les objets génériques
        specific_objects = [obj for obj in objects if obj not in ['photo', 'image', 'colorful scene']]
        
        # Stratégie 1: Lieu + Objet principal
        if locations and specific_objects:
            city = locations[0].get('city', '')
            main_object = self._translate_object(specific_objects[0])
            return f"{main_object.capitalize()} à {city}"
        
        # Stratégie 2: Émotion + Objet
        if emotions and specific_objects:
            emotion = emotions[0]
            main_object = self._translate_object(specific_objects[0])
            
            if emotion == 'joyeuse':
                return f"{main_object.capitalize()} joyeux"
            elif emotion == 'paisible':
                return f"{main_object.capitalize()} serein"
            elif emotion == 'dramatique':
                return f"{main_object.capitalize()} spectaculaire"
            else:
                return f"{main_object.capitalize()} {emotion}"
        
        # Stratégie 3: Objets multiples
        if len(specific_objects) >= 2:
            obj1 = self._translate_object(specific_objects[0])
            obj2 = self._translate_object(specific_objects[1])
            return f"{obj1.capitalize()} et {obj2}"
        
        # Stratégie 4: Objet unique
        if specific_objects:
            main_object = self._translate_object(specific_objects[0])
            return f"{main_object.capitalize()}"
        
        # Stratégie 5: Basé sur les couleurs dominantes
        if colors and len(colors) >= 2:
            color_desc = self._describe_color_palette(colors)
            return f"Composition {color_desc}"
        
        # Par défaut
        return "Photographie capturée"
    
    def generate_smart_description(self, analysis_results: Dict) -> str:
        """
        Génère une description riche et contextuelle
        
        Args:
            analysis_results: Résultats complets de l'analyse Vision AI
            
        Returns:
            Description détaillée et engageante
        """
        objects = [obj['object'] for obj in analysis_results.get('detected_objects', [])]
        colors = analysis_results.get('dominant_colors', [])
        emotions = [emo['emotion'] for emo in analysis_results.get('detected_emotions', [])]
        locations = analysis_results.get('detected_locations', [])
        
        description_parts = []
        
        # Filtrer les objets génériques
        specific_objects = [obj for obj in objects if obj not in ['photo', 'image', 'colorful scene']]
        
        # 1. Introduction basée sur le contenu
        if locations:
            # Si c'est un lieu connu
            location_info = locations[0]
            city = location_info.get('city', '')
            landmark = location_info.get('landmark', '')
            
            if landmark and city:
                description_parts.append(f"Photographie de {landmark} situé à {city}")
            elif city:
                description_parts.append(f"Image capturée à {city}")
        elif specific_objects:
            # Basé sur les objets
            if len(specific_objects) == 1:
                obj_trans = self._translate_object(specific_objects[0])
                description_parts.append(f"Photographie présentant {obj_trans}")
            elif len(specific_objects) == 2:
                obj1 = self._translate_object(specific_objects[0])
                obj2 = self._translate_object(specific_objects[1])
                description_parts.append(f"Image montrant {obj1} et {obj2}")
            else:
                obj1 = self._translate_object(specific_objects[0])
                obj2 = self._translate_object(specific_objects[1])
                description_parts.append(f"Composition visuelle de {obj1}, {obj2} et autres éléments")
        else:
            description_parts.append("Photographie")
        
        # 2. Description des couleurs
        if colors and len(colors) >= 3:
            color_desc = self._describe_color_palette(colors)
            description_parts.append(f"caractérisée par {color_desc}")
        
        # 3. Ambiance et émotion
        if emotions:
            emotion = emotions[0]
            if emotion in self.emotion_descriptions:
                description_parts.append(f"créant {self.emotion_descriptions[emotion]}")
            else:
                description_parts.append(f"à l'ambiance {emotion}")
        
        # 4. Détails supplémentaires sur les couleurs
        if colors:
            num_colors = len(colors)
            if num_colors >= 5:
                description_parts.append(f"Une palette riche de {num_colors} couleurs dominantes enrichit cette composition")
            elif num_colors >= 3:
                description_parts.append(f"avec {num_colors} couleurs principales harmonieusement équilibrées")
        
        # Assembler la description
        if len(description_parts) == 1:
            # Description minimale enrichie
            return f"{description_parts[0]} capturée avec soin, révélant une composition visuelle unique."
        else:
            # Joindre les parties avec ponctuation appropriée
            description = description_parts[0]
            
            for i, part in enumerate(description_parts[1:], 1):
                if i == 1:
                    description += ", " + part
                elif i == len(description_parts) - 1:
                    description += ". " + part
                else:
                    description += ", " + part
            
            if not description.endswith('.'):
                description += "."
            
            return description
    
    def _translate_object(self, obj: str) -> str:
        """Traduit et améliore le nom d'un objet détecté"""
        return self.object_translations.get(obj.lower(), obj)
    
    def _describe_color_palette(self, colors: List[Dict]) -> str:
        """Génère une description de la palette de couleurs"""
        if not colors:
            return "des tons variés"
        
        color_names = [self._get_color_family(c.get('name', '')) for c in colors[:3]]
        unique_colors = list(dict.fromkeys(color_names))
        
        if len(unique_colors) == 1:
            return f"une palette de tons {unique_colors[0]}s"
        elif len(unique_colors) == 2:
            return f"des tonalités {unique_colors[0]}es et {unique_colors[1]}es"
        else:
            return f"une harmonie de {unique_colors[0]}, {unique_colors[1]} et {unique_colors[2]}"
    
    def _get_color_family(self, color_name: str) -> str:
        """Obtient la famille de couleur"""
        color_name = color_name.lower()
        
        warm_colors = ['rouge', 'orange', 'jaune', 'rose', 'magenta']
        cool_colors = ['bleu', 'vert', 'cyan', 'violet']
        neutral_colors = ['gris', 'blanc', 'noir', 'beige', 'marron']
        
        for warm in warm_colors:
            if warm in color_name:
                return 'chaud'
        
        for cool in cool_colors:
            if cool in color_name:
                return 'froid'
        
        for neutral in neutral_colors:
            if neutral in color_name:
                return 'neutre'
        
        return 'coloré'


# Instance globale
description_enhancer = DescriptionEnhancer()


def enhance_analysis_results(analysis_results: Dict) -> Dict:
    """
    Améliore les titres et descriptions dans les résultats d'analyse
    
    Args:
        analysis_results: Résultats bruts de l'analyse Vision AI
        
    Returns:
        Résultats améliorés avec titre et description enrichis
    """
    # Générer un titre intelligent
    smart_title = description_enhancer.generate_smart_title(analysis_results)
    
    # Générer une description riche
    smart_description = description_enhancer.generate_smart_description(analysis_results)
    
    # Ajouter aux résultats
    analysis_results['ai_title'] = smart_title
    analysis_results['image_description'] = smart_description
    
    return analysis_results
