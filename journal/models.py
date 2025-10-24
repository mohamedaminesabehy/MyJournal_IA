from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import os
from PIL import Image
import uuid

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.username

class Category(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, null=True)
    # Passage à ManyToMany: une catégorie peut appartenir à plusieurs utilisateurs,
    # et un utilisateur peut avoir plusieurs catégories
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')  # Au lieu de ManyToManyField
    def __str__(self):
        return self.name


# ==================== GALERIE INTELLIGENTE ====================

def media_upload_path(instance, filename):
    """Génère un chemin unique pour chaque média uploadé"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join('gallery', instance.user.username, filename)


class Media(models.Model):
    """Modèle principal pour stocker les médias (images/vidéos)"""
    
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Vidéo'),
        ('audio', 'Audio'),
    ]
    
    # Informations de base
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media')
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    
    # Fichier
    file = models.FileField(
        upload_to=media_upload_path,
        validators=[FileExtensionValidator(
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'avi', 'mov', 'mp3', 'wav']
        )]
    )
    thumbnail = models.ImageField(upload_to='gallery/thumbnails/', blank=True, null=True)
    
    # Métadonnées
    file_size = models.BigIntegerField(default=0)  # en bytes
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)  # pour vidéos/audio en secondes
    
    # Organisation
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='media')
    album = models.CharField(max_length=100, blank=True, null=True)
    
    # États et dates
    is_favorite = models.BooleanField(default=False)
    is_analyzed = models.BooleanField(default=False)  # IA a analysé ?
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Média'
        verbose_name_plural = 'Médias'
    
    def __str__(self):
        return self.title or f"{self.media_type} - {self.uploaded_at.strftime('%Y-%m-%d')}"
    
    def save(self, *args, **kwargs):
        """Override save pour extraire métadonnées automatiquement"""
        if self.file and not self.file_size:
            self.file_size = self.file.size
            
            # Déterminer le type de média
            ext = self.file.name.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                self.media_type = 'image'
            elif ext in ['mp4', 'avi', 'mov', 'webm']:
                self.media_type = 'video'
            elif ext in ['mp3', 'wav', 'ogg']:
                self.media_type = 'audio'
        
        super().save(*args, **kwargs)
    
    @property
    def file_size_display(self):
        """Affiche la taille en format lisible"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class MediaAnalysis(models.Model):
    """Résultats de l'analyse IA pour chaque média"""
    
    media = models.OneToOneField(Media, on_delete=models.CASCADE, related_name='analysis')
    
    # Vision AI - Détection d'objets et lieux
    detected_objects = models.JSONField(default=list, blank=True)  # ["plage", "palmier", "coucher de soleil"]
    detected_locations = models.JSONField(default=list, blank=True)  # [{"name": "Tour Eiffel", "city": "Paris"}]
    detected_faces = models.IntegerField(default=0)  # Nombre de visages
    
    # Vision AI - Analyse couleurs
    dominant_colors = models.JSONField(default=list, blank=True)  # [{"color": "#FF5733", "percentage": 45}]
    color_palette = models.JSONField(default=list, blank=True)  # Liste des couleurs principales
    
    # Vision AI - Émotions et ambiance
    detected_emotions = models.JSONField(default=list, blank=True)  # ["joie", "sérénité"]
    mood = models.CharField(max_length=50, blank=True, null=True)  # "joyeuse", "mélancolique"
    
    # Vision AI - OCR (texte dans l'image)
    extracted_text = models.TextField(blank=True, null=True)
    
    # Generative AI - Contenu généré
    ai_title = models.CharField(max_length=200, blank=True, null=True)  # Titre créatif généré
    ai_description = models.TextField(blank=True, null=True)  # Description poétique
    ai_summary = models.TextField(blank=True, null=True)  # Pour vidéos
    
    # Generative AI - Suggestions
    suggested_tags = models.JSONField(default=list, blank=True)
    suggested_filters = models.JSONField(default=list, blank=True)  # ["vintage", "noir et blanc"]
    creative_suggestions = models.TextField(blank=True, null=True)
    
    # Métadonnées d'analyse
    vision_api_used = models.CharField(max_length=50, blank=True, null=True)  # "Google Vision", "CLIP"
    generative_api_used = models.CharField(max_length=50, blank=True, null=True)  # "GPT-4", "Gemini"
    confidence_score = models.FloatField(default=0.0)  # Score de confiance global (0-1)
    
    analyzed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Analyse IA'
        verbose_name_plural = 'Analyses IA'
    
    def __str__(self):
        return f"Analyse de {self.media.title or self.media.file.name}"
    
    @property
    def all_tags(self):
        """Combine tous les tags détectés"""
        tags = set()
        tags.update(self.detected_objects or [])
        tags.update(self.suggested_tags or [])
        tags.update(self.detected_emotions or [])
        return list(tags)


class MediaTag(models.Model):
    """Tags pour organiser les médias (combinaison de tags manuels et IA)"""
    
    TAG_SOURCES = [
        ('manual', 'Manuel'),
        ('ai', 'IA'),
        ('system', 'Système'),
    ]
    
    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50)
    source = models.CharField(max_length=10, choices=TAG_SOURCES, default='manual')
    confidence = models.FloatField(default=1.0)  # Pour tags IA (0-1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('media', 'name')
        ordering = ['-confidence', 'name']
        verbose_name = 'Tag Média'
        verbose_name_plural = 'Tags Média'
    
    def __str__(self):
        return f"{self.name} ({self.source})"


class SmartAlbum(models.Model):
    """Albums intelligents créés automatiquement par l'IA"""
    
    ALBUM_TYPES = [
        ('auto', 'Automatique'),  # Créé par IA
        ('manual', 'Manuel'),     # Créé par utilisateur
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='smart_albums')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    album_type = models.CharField(max_length=10, choices=ALBUM_TYPES, default='manual')
    
    # Critères pour albums automatiques
    filter_criteria = models.JSONField(default=dict, blank=True)  # {"location": "Paris", "mood": "joyeuse"}
    
    # Médias
    media = models.ManyToManyField(Media, related_name='smart_albums', blank=True)
    
    # Métadonnées
    cover_image = models.ForeignKey(Media, on_delete=models.SET_NULL, null=True, blank=True, related_name='album_covers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Album Intelligent'
        verbose_name_plural = 'Albums Intelligents'
    
    def __str__(self):
        return self.name
class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200)
    content = models.CharField(max_length=5000)
    location = models.CharField(max_length=255, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_draft = models.BooleanField(default=False)
    emotion = models.CharField(max_length=50, blank=True, null=True)
    emotion_confidence = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.title
    
    def get_emotion_icon(self):
        """Return an icon based on the predicted emotion"""
        emotion_icons = {
            'joy': 'fas fa-smile text-warning',
            'sadness': 'fas fa-sad-tear text-primary',
            'love': 'fas fa-heart text-danger',
            'anger': 'fas fa-angry text-danger',
            'fear': 'fas fa-frown text-dark',
            'surprise': 'fas fa-surprise text-info'
        }
        return emotion_icons.get(self.emotion, 'fas fa-meh text-muted')
    
    def get_emotion_display(self):
        """Return a human-readable emotion name"""
        emotions = {
            'joy': 'Joie',
            'sadness': 'Tristesse', 
            'love': 'Amour',
            'anger': 'Colère',
            'fear': 'Peur',
            'surprise': 'Surprise'
        }
        return emotions.get(self.emotion, 'Neutre')


class ActivityRecommendation(models.Model):
    """Modèle pour stocker les recommandations d'activités générées par l'IA"""
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='recommendations')
    emotion = models.CharField(max_length=50)
    confidence = models.FloatField(default=0.5)
    recommendations = models.JSONField()  # Stocke les recommandations sous format JSON
    encouragement = models.TextField()
    color = models.CharField(max_length=7, default='#6366f1')  # Code couleur hex
    icon = models.CharField(max_length=50, default='fas fa-lightbulb')
    
    # Nouveaux champs pour l'enrichissement Perplexity
    enriched_content = models.JSONField(null=True, blank=True)  # Contenu enrichi par Perplexity
    has_enrichment = models.BooleanField(default=False)  # Indique si l'enrichissement a été généré
    enrichment_generated_at = models.DateTimeField(null=True, blank=True)  # Timestamp de l'enrichissement
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Recommandations pour '{self.note.title}' - {self.emotion}"
    
    def get_multimedia_content(self):
        """Retourne le contenu multimédia enrichi s'il existe"""
        if self.enriched_content and 'multimedia_content' in self.enriched_content:
            return self.enriched_content['multimedia_content']
        return None
    
    def get_explanation(self):
        """Retourne l'explication scientifique enrichie s'il existe"""
        if self.enriched_content and 'explanation' in self.enriched_content:
            return self.enriched_content['explanation']
        return None
    
    def get_local_suggestions(self):
        """Retourne les suggestions locales enrichies s'il existe"""
        if self.enriched_content and 'local_suggestions' in self.enriched_content:
            return self.enriched_content['local_suggestions']
        return None
