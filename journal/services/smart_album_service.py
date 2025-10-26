"""
Service de création automatique d'albums intelligents basés sur l'IA
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from django.db.models import Count, Q
from django.contrib.auth.models import User
from ..models import Media, MediaAnalysis, SmartAlbum

logger = logging.getLogger(__name__)


class SmartAlbumService:
    """Service pour créer et gérer des albums intelligents automatiquement"""
    
    def __init__(self):
        self.album_rules = {
            # Albums par lieux/monuments
            'beaches': {
                'name': '🏖️ Plages et Mer',
                'description': 'Toutes vos photos de plages et bords de mer',
                'objects': ['mer', 'plage', 'sable', 'océan', 'beach', 'ocean'],
                'min_media': 1,
                'icon': '🏖️'
            },
            'monuments': {
                'name': '🏛️ Monuments et Architecture',
                'description': 'Photos de monuments et bâtiments remarquables',
                'objects': ['monument', 'building', 'architecture', 'tower', 'château', 'église', 'place'],
                'locations': ['Tour Eiffel', 'Big Ben', 'Colosseum', 'Statue of Liberty', 'Pyramides', 'Arc de Triomphe', 'Architecture moderne'],
                'min_media': 1,
                'icon': '🏛️'
            },
            'nature': {
                'name': '🌳 Nature et Paysages',
                'description': 'Vos plus beaux paysages naturels',
                'objects': ['tree', 'forest', 'mountain', 'river', 'lake', 'arbre', 'montagne', 'forêt'],
                'min_media': 3,
                'icon': '🌳'
            },
            
            # Albums par personnes
            'people': {
                'name': '👥 Personnes',
                'description': 'Photos avec des personnes',
                'objects': ['person', 'personne', 'people', 'face', 'visage'],
                'min_media': 1,
                'icon': '👥'
            },
            
            # Albums par nourriture
            'food': {
                'name': '🍕 Nourriture',
                'description': 'Vos photos culinaires',
                'objects': ['food', 'pizza', 'burger', 'cake', 'nourriture', 'gâteau'],
                'min_media': 2,
                'icon': '🍕'
            },
            
            # Albums par émotions
            'peaceful': {
                'name': '😌 Moments Paisibles',
                'description': 'Photos à l\'ambiance calme et sereine',
                'emotions': ['peaceful', 'calm', 'serene', 'quiet'],
                'min_media': 3,
                'icon': '😌'
            },
            'joyful': {
                'name': '😊 Moments Joyeux',
                'description': 'Photos pleines de joie et de bonheur',
                'emotions': ['joyful', 'happy', 'cheerful', 'celebration'],
                'min_media': 3,
                'icon': '😊'
            },
            
            # Albums par couleurs
            'blue_dominant': {
                'name': '💙 Dominante Bleue',
                'description': 'Photos aux tons bleus',
                'color_keywords': ['bleu', 'blue', 'cyan', 'turquoise'],
                'min_media': 3,
                'icon': '💙'
            },
            'warm_colors': {
                'name': '🧡 Tons Chauds',
                'description': 'Photos aux couleurs chaudes (rouge, orange, jaune)',
                'color_keywords': ['rouge', 'orange', 'jaune', 'red', 'yellow'],
                'min_media': 3,
                'icon': '🧡'
            },
            
            # Albums par période
            'recent': {
                'name': '📅 Cette Semaine',
                'description': 'Photos uploadées cette semaine',
                'days_ago': 7,
                'min_media': 2,
                'icon': '📅'
            },
            'this_month': {
                'name': '📆 Ce Mois',
                'description': 'Photos uploadées ce mois',
                'days_ago': 30,
                'min_media': 3,
                'icon': '📆'
            },
            
            # Albums par qualité
            'favorites': {
                'name': '⭐ Favoris',
                'description': 'Vos photos favorites',
                'is_favorite': True,
                'min_media': 1,
                'icon': '⭐'
            },
        }
    
    def create_all_smart_albums(self, user: User, force_recreate: bool = False) -> Dict:
        """
        Crée tous les albums intelligents pour un utilisateur
        
        Args:
            user: L'utilisateur
            force_recreate: Si True, supprime et recrée tous les albums auto
            
        Returns:
            Dict avec les statistiques de création
        """
        logger.info(f"🎨 Création d'albums intelligents pour {user.username}")
        
        stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'albums': []
        }
        
        # Supprimer les anciens albums auto si demandé
        if force_recreate:
            deleted_count = SmartAlbum.objects.filter(
                user=user,
                album_type='auto'
            ).delete()[0]
            logger.info(f"🗑️ {deleted_count} anciens albums supprimés")
        
        # Créer chaque type d'album
        for album_key, album_config in self.album_rules.items():
            try:
                result = self._create_album_by_rule(user, album_key, album_config)
                
                if result['created']:
                    stats['created'] += 1
                    stats['albums'].append(result['album'])
                    logger.info(f"✅ Album créé: {result['album'].name} ({result['media_count']} médias)")
                elif result['updated']:
                    stats['updated'] += 1
                    logger.info(f"🔄 Album mis à jour: {result['album'].name} ({result['media_count']} médias)")
                else:
                    stats['skipped'] += 1
                    logger.info(f"⏭️ Album ignoré: {album_config['name']} (pas assez de médias)")
                    
            except Exception as e:
                logger.error(f"❌ Erreur création album {album_key}: {e}")
        
        logger.info(f"✨ Terminé! Créés: {stats['created']}, Mis à jour: {stats['updated']}, Ignorés: {stats['skipped']}")
        return stats
    
    def _create_album_by_rule(self, user: User, album_key: str, config: Dict) -> Dict:
        """
        Crée un album basé sur une règle
        
        Returns:
            Dict avec 'created', 'updated', 'album', 'media_count'
        """
        # Récupérer les médias correspondants
        media_list = self._get_media_by_criteria(user, config)
        
        # Vérifier le minimum requis
        if len(media_list) < config.get('min_media', 1):
            return {
                'created': False,
                'updated': False,
                'album': None,
                'media_count': len(media_list)
            }
        
        # Créer ou mettre à jour l'album
        album_name = config['name']
        
        try:
            album = SmartAlbum.objects.get(
                user=user,
                name=album_name,
                album_type='auto'
            )
            created = False
        except SmartAlbum.DoesNotExist:
            # Utiliser .create() au lieu de .save() pour Djongo
            album = SmartAlbum.objects.create(
                user=user,
                name=album_name,
                album_type='auto',
                description=config['description'],
                filter_criteria={
                    'rule_key': album_key,
                    **config
                }
            )
            created = True
        
        # Mettre à jour les médias - Utiliser .add() au lieu de .set() pour Djongo
        album.media.clear()  # Vider d'abord
        for media in media_list:
            album.media.add(media)
        
        # Définir l'image de couverture (le plus récent)
        if media_list:
            album.cover_image = media_list[0]
            album.save()
        
        return {
            'created': created,
            'updated': not created,
            'album': album,
            'media_count': len(media_list)
        }
    
    def _get_media_by_criteria(self, user: User, config: Dict) -> List[Media]:
        """
        Récupère les médias correspondant aux critères
        """
        # Base query: médias de l'utilisateur
        # Note: Djongo a des problèmes avec les filtres booléens, donc on filtre après
        queryset = Media.objects.filter(
            user=user,
            media_type='image'  # Pour l'instant, seulement les images
        )
        
        # Filtre par période
        if 'days_ago' in config:
            date_limit = datetime.now() - timedelta(days=config['days_ago'])
            queryset = queryset.filter(uploaded_at__gte=date_limit)
        
        # Filtre par favoris
        if config.get('is_favorite'):
            # Djongo workaround: filtrer en Python
            queryset = [m for m in queryset if m.is_favorite]
            queryset = Media.objects.filter(id__in=[m.id for m in queryset]) if queryset else Media.objects.none()
        
        # Filtrer seulement les médias analysés (workaround Djongo)
        analyzed_ids = []
        for media in queryset:
            if media.is_analyzed:
                try:
                    # Tenter d'accéder à l'analyse
                    _ = media.analysis
                    analyzed_ids.append(media.id)
                except MediaAnalysis.DoesNotExist:
                    # Pas d'analyse pour ce média
                    pass
                except MediaAnalysis.MultipleObjectsReturned:
                    # Plusieurs analyses (erreur de données) - prendre le média quand même
                    logger.warning(f"⚠️ Plusieurs analyses pour media {media.id}")
                    analyzed_ids.append(media.id)
        
        if not analyzed_ids:
            return []
        
        queryset = Media.objects.filter(id__in=analyzed_ids)
        
        # Filtre par objets détectés
        if 'objects' in config:
            matching_ids = []
            for media in queryset:
                try:
                    analysis = media.analysis
                    if analysis.detected_objects:
                        # Vérifier si au moins un objet correspond
                        detected = analysis.detected_objects
                        if isinstance(detected, list):
                            for obj in config['objects']:
                                if any(obj.lower() in str(d).lower() for d in detected):
                                    matching_ids.append(media.id)
                                    break
                except (MediaAnalysis.DoesNotExist, MediaAnalysis.MultipleObjectsReturned) as e:
                    if isinstance(e, MediaAnalysis.MultipleObjectsReturned):
                        # Utiliser la première analyse en cas de doublons
                        analysis = MediaAnalysis.objects.filter(media=media).first()
                        if analysis and analysis.detected_objects:
                            detected = analysis.detected_objects
                            if isinstance(detected, list):
                                for obj in config['objects']:
                                    if any(obj.lower() in str(d).lower() for d in detected):
                                        matching_ids.append(media.id)
                                        break
            
            if not matching_ids:
                return []
            queryset = Media.objects.filter(id__in=matching_ids)
        
        # Filtre par lieux
        if 'locations' in config:
            matching_ids = []
            for media in queryset:
                try:
                    analysis = media.analysis
                    if analysis.detected_locations:
                        detected = analysis.detected_locations
                        if isinstance(detected, list):
                            for loc in config['locations']:
                                if any(loc.lower() in str(d).lower() for d in detected):
                                    matching_ids.append(media.id)
                                    break
                except (MediaAnalysis.DoesNotExist, MediaAnalysis.MultipleObjectsReturned) as e:
                    if isinstance(e, MediaAnalysis.MultipleObjectsReturned):
                        # Utiliser la première analyse en cas de doublons
                        analysis = MediaAnalysis.objects.filter(media=media).first()
                        if analysis and analysis.detected_locations:
                            detected = analysis.detected_locations
                            if isinstance(detected, list):
                                for loc in config['locations']:
                                    if any(loc.lower() in str(d).lower() for d in detected):
                                        matching_ids.append(media.id)
                                        break
            
            if not matching_ids:
                return []
            queryset = Media.objects.filter(id__in=matching_ids)
        
        # Filtre par émotions
        if 'emotions' in config:
            matching_ids = []
            for media in queryset:
                try:
                    analysis = media.analysis
                    if analysis.detected_emotions:
                        detected = analysis.detected_emotions
                        if isinstance(detected, list):
                            for emotion in config['emotions']:
                                if any(emotion.lower() in str(d).lower() for d in detected):
                                    matching_ids.append(media.id)
                                    break
                except (MediaAnalysis.DoesNotExist, MediaAnalysis.MultipleObjectsReturned) as e:
                    if isinstance(e, MediaAnalysis.MultipleObjectsReturned):
                        # Utiliser la première analyse en cas de doublons
                        analysis = MediaAnalysis.objects.filter(media=media).first()
                        if analysis and analysis.detected_emotions:
                            detected = analysis.detected_emotions
                            if isinstance(detected, list):
                                for emotion in config['emotions']:
                                    if any(emotion.lower() in str(d).lower() for d in detected):
                                        matching_ids.append(media.id)
                                        break
            
            if not matching_ids:
                return []
            queryset = Media.objects.filter(id__in=matching_ids)
        
        # Filtre par couleurs
        if 'color_keywords' in config:
            matching_ids = []
            for media in queryset:
                try:
                    analysis = media.analysis
                    if analysis.dominant_colors:
                        colors = analysis.dominant_colors
                        if isinstance(colors, list):
                            colors_str = ' '.join([str(c) for c in colors]).lower()
                            for color in config['color_keywords']:
                                if color.lower() in colors_str:
                                    matching_ids.append(media.id)
                                    break
                except (MediaAnalysis.DoesNotExist, MediaAnalysis.MultipleObjectsReturned) as e:
                    if isinstance(e, MediaAnalysis.MultipleObjectsReturned):
                        # Utiliser la première analyse en cas de doublons
                        analysis = MediaAnalysis.objects.filter(media=media).first()
                        if analysis and analysis.dominant_colors:
                            colors = analysis.dominant_colors
                            if isinstance(colors, list):
                                colors_str = ' '.join([str(c) for c in colors]).lower()
                                for color in config['color_keywords']:
                                    if color.lower() in colors_str:
                                        matching_ids.append(media.id)
                                        break
            
            if not matching_ids:
                return []
            queryset = Media.objects.filter(id__in=matching_ids)
        
        # Distinct et ordonné par date décroissante
        return list(queryset.distinct().order_by('-uploaded_at'))
    
    def get_album_suggestions(self, user: User) -> List[Dict]:
        """
        Suggère des albums potentiels sans les créer
        
        Returns:
            Liste de suggestions avec nombre de médias potentiels
        """
        suggestions = []
        
        for album_key, config in self.album_rules.items():
            media_list = self._get_media_by_criteria(user, config)
            
            if len(media_list) >= config.get('min_media', 1):
                suggestions.append({
                    'key': album_key,
                    'name': config['name'],
                    'description': config['description'],
                    'icon': config.get('icon', '📁'),
                    'media_count': len(media_list),
                    'can_create': True
                })
        
        # Trier par nombre de médias décroissant
        suggestions.sort(key=lambda x: x['media_count'], reverse=True)
        return suggestions
    
    def update_album(self, album_id: int) -> Optional[SmartAlbum]:
        """
        Met à jour un album intelligent existant
        """
        try:
            album = SmartAlbum.objects.get(id=album_id, album_type='auto')
            
            # Récupérer la règle d'origine
            rule_key = album.filter_criteria.get('rule_key')
            if not rule_key or rule_key not in self.album_rules:
                logger.warning(f"⚠️ Règle non trouvée pour l'album {album.name}")
                return None
            
            config = self.album_rules[rule_key]
            media_list = self._get_media_by_criteria(album.user, config)
            
            # Mettre à jour
            album.media.set(media_list)
            if media_list:
                album.cover_image = media_list[0]
            album.save()
            
            logger.info(f"🔄 Album mis à jour: {album.name} ({len(media_list)} médias)")
            return album
            
        except SmartAlbum.DoesNotExist:
            logger.error(f"❌ Album {album_id} non trouvé")
            return None
    
    def delete_empty_albums(self, user: User) -> int:
        """
        Supprime les albums automatiques vides
        """
        empty_albums = SmartAlbum.objects.filter(
            user=user,
            album_type='auto',
            media__isnull=True
        )
        count = empty_albums.count()
        empty_albums.delete()
        
        logger.info(f"🗑️ {count} albums vides supprimés")
        return count


# Instance globale du service
smart_album_service = SmartAlbumService()
