from django.db import models
from django.contrib.auth.models import User
<<<<<<< HEAD
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date
from django.utils.text import slugify

=======
from django.core.validators import FileExtensionValidator
import os
from PIL import Image
import uuid
>>>>>>> origin/yassineJawadi

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.username

class Category(models.Model):
    name = models.CharField(max_length=100)
<<<<<<< HEAD
    icon = models.CharField(max_length=50, blank=True, default='📁')
    # Passage à ManyToMany: une catégorie peut appartenir à plusieurs utilisateurs,
    # et un utilisateur peut avoir plusieurs catégories
    users = models.ManyToManyField(User, related_name='categories', blank=True)

    def __str__(self):
        return self.name

=======
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
>>>>>>> origin/yassineJawadi
class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200)
    content = models.CharField(max_length=5000)
<<<<<<< HEAD
    location = models.CharField(max_length=255, blank=True)
=======
    location = models.CharField(max_length=255, blank=True, null=True)
>>>>>>> origin/yassineJawadi
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_draft = models.BooleanField(default=False)
<<<<<<< HEAD
    emotion = models.CharField(max_length=50, blank=True)
=======
    emotion = models.CharField(max_length=50, blank=True, null=True)
>>>>>>> origin/yassineJawadi
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


<<<<<<< HEAD
class Goal(models.Model):
    STATUS_ONGOING = 'ongoing'
    STATUS_COMPLETED = 'completed'
    STATUS_ABANDONED = 'abandoned'

    STATUS_CHOICES = [
        (STATUS_ONGOING, 'En cours'),
        (STATUS_COMPLETED, 'Terminé'),
        (STATUS_ABANDONED, 'Abandonné'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ONGOING)
    motivation_level = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)], default=5)
    linked_entries = models.ManyToManyField('Note', related_name='goals', blank=True)
    # Distinctive fields to differentiate Goal from Note
    PRIORITY_LOW = 1
    PRIORITY_MEDIUM = 2
    PRIORITY_HIGH = 3
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Faible'),
        (PRIORITY_MEDIUM, 'Moyenne'),
        (PRIORITY_HIGH, 'Haute'),
    ]

    VISIBILITY_PRIVATE = 'private'
    VISIBILITY_PUBLIC = 'public'
    VISIBILITY_CHOICES = [
        (VISIBILITY_PRIVATE, 'Privé'),
        (VISIBILITY_PUBLIC, 'Public'),
    ]

    # New fields
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default=VISIBILITY_PRIVATE)
    reward = models.CharField(max_length=200, blank=True)
    difficulty = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    recurrence = models.CharField(max_length=20, blank=True)
    # Milestones stored as a small JSON array of objects {title: str, done: bool, due: str}
    milestones = models.JSONField(blank=True, null=True)
    # Slug to provide friendly URLs and distinguish from Note titles
    slug = models.SlugField(max_length=220, blank=True, db_index=True)
    # Cached progress (computed on save) to speed up list rendering
    progress_cached = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        # Note: Django Meta constraints may not work perfectly with MongoDB/Djongo
        # We handle uniqueness in the save() method

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def progress_pct(self):
        """Return percentage of completed milestones (0-100). If no milestones, return None."""
        if not isinstance(self.milestones, list) or len(self.milestones) == 0:
            return None
        try:
            total = len(self.milestones)
            done_count = sum(1 for m in self.milestones if isinstance(m, dict) and m.get('done'))
            pct = int((done_count / total) * 100)
            return max(0, min(100, pct))
        except Exception:
            return None

    def save(self, *args, **kwargs):
        """Generate a slug and update cached progress on save."""
        # Determine if this is an update (has _id attribute from MongoDB)
        is_update = hasattr(self, '_id') and self._id is not None
        
        # Only generate slug if it doesn't exist (new object)
        if not self.slug:
            if self.title:
                base = slugify(self.title)[:200]
                slug = base
                counter = 1
                # Ensure uniqueness - check against all existing slugs
                while type(self).objects.filter(slug=slug).exclude(pk=self.pk if self.pk else None).exists():
                    slug = f"{base}-{counter}"
                    counter += 1
                self.slug = slug
            else:
                # If no title and no slug, generate a random one
                import uuid
                self.slug = str(uuid.uuid4())[:8]
        
        # update cached progress
        pct = self.progress_pct()
        if pct is not None:
            self.progress_cached = pct

        # For updates, ensure we have the pk set
        if is_update and not self.pk:
            self.pk = self._id

        super().save(*args, **kwargs)
=======
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


class Affirmation(models.Model):
    TONE_CHOICES = [
        ('calm', 'Calm'),
        ('motivational', 'Motivational'),
        ('self_compassion', 'Self-Compassion'),
        ('focus', 'Focus'),
        ('confidence', 'Confidence'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_affirmations',  # unique name, no clash
    )
    text = models.CharField(max_length=240)
    tone = models.CharField(max_length=32, choices=TONE_CHOICES, default='calm')
    topic = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:60]
>>>>>>> origin/yassineJawadi
