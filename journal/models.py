from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from datetime import date
from django.utils.text import slugify
import os
from PIL import Image
import uuid


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username


class Category(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, default='📁')
    users = models.ManyToManyField(User, related_name='categories', blank=True)

    def __str__(self):
        return self.name


def media_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join('gallery', instance.user.username, filename)


class Media(models.Model):
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Vidéo'),
        ('audio', 'Audio'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media')
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)

    file = models.FileField(
        upload_to=media_upload_path,
        validators=[FileExtensionValidator(
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'avi', 'mov', 'mp3', 'wav']
        )]
    )
    thumbnail = models.ImageField(upload_to='gallery/thumbnails/', blank=True, null=True)
    file_size = models.BigIntegerField(default=0)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='media')
    album = models.CharField(max_length=100, blank=True, null=True)
    is_favorite = models.BooleanField(default=False)
    is_analyzed = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Média'
        verbose_name_plural = 'Médias'

    def __str__(self):
        return self.title or f"{self.media_type} - {self.uploaded_at.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            self.file_size = self.file.size
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
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class MediaAnalysis(models.Model):
    media = models.OneToOneField(Media, on_delete=models.CASCADE, related_name='analysis')
    detected_objects = models.JSONField(default=list, blank=True)
    detected_locations = models.JSONField(default=list, blank=True)
    detected_faces = models.IntegerField(default=0)
    dominant_colors = models.JSONField(default=list, blank=True)
    color_palette = models.JSONField(default=list, blank=True)
    detected_emotions = models.JSONField(default=list, blank=True)
    mood = models.CharField(max_length=50, blank=True, null=True)
    extracted_text = models.TextField(blank=True, null=True)
    ai_title = models.CharField(max_length=200, blank=True, null=True)
    ai_description = models.TextField(blank=True, null=True)
    ai_summary = models.TextField(blank=True, null=True)
    suggested_tags = models.JSONField(default=list, blank=True)
    suggested_filters = models.JSONField(default=list, blank=True)
    creative_suggestions = models.TextField(blank=True, null=True)
    vision_api_used = models.CharField(max_length=50, blank=True, null=True)
    generative_api_used = models.CharField(max_length=50, blank=True, null=True)
    confidence_score = models.FloatField(default=0.0)
    analyzed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Analyse IA'
        verbose_name_plural = 'Analyses IA'

    def __str__(self):
        return f"Analyse de {self.media.title or self.media.file.name}"

    @property
    def all_tags(self):
        tags = set()
        tags.update(self.detected_objects or [])
        tags.update(self.suggested_tags or [])
        tags.update(self.detected_emotions or [])
        return list(tags)


class MediaTag(models.Model):
    TAG_SOURCES = [
        ('manual', 'Manuel'),
        ('ai', 'IA'),
        ('system', 'Système'),
    ]

    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50)
    source = models.CharField(max_length=10, choices=TAG_SOURCES, default='manual')
    confidence = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('media', 'name')
        ordering = ['-confidence', 'name']
        verbose_name = 'Tag Média'
        verbose_name_plural = 'Tags Média'

    def __str__(self):
        return f"{self.name} ({self.source})"


class SmartAlbum(models.Model):
    ALBUM_TYPES = [
        ('auto', 'Automatique'),
        ('manual', 'Manuel'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='smart_albums')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    album_type = models.CharField(max_length=10, choices=ALBUM_TYPES, default='manual')
    filter_criteria = models.JSONField(default=dict, blank=True)
    media = models.ManyToManyField(Media, related_name='smart_albums', blank=True)
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
        emotions = {
            'joy': 'Joie',
            'sadness': 'Tristesse',
            'love': 'Amour',
            'anger': 'Colère',
            'fear': 'Peur',
            'surprise': 'Surprise'
        }
        return emotions.get(self.emotion, 'Neutre')


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

    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default=VISIBILITY_PRIVATE)
    reward = models.CharField(max_length=200, blank=True)
    difficulty = models.IntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    recurrence = models.CharField(max_length=20, blank=True)
    milestones = models.JSONField(blank=True, null=True)
    slug = models.SlugField(max_length=220, blank=True, db_index=True)
    progress_cached = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def progress_pct(self):
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
        is_update = hasattr(self, '_id') and self._id is not None
        if not self.slug:
            if self.title:
                base = slugify(self.title)[:200]
                slug = base
                counter = 1
                while type(self).objects.filter(slug=slug).exclude(pk=self.pk if self.pk else None).exists():
                    slug = f"{base}-{counter}"
                    counter += 1
                self.slug = slug
            else:
                import uuid
                self.slug = str(uuid.uuid4())[:8]

        pct = self.progress_pct()
        if pct is not None:
            self.progress_cached = pct

        if is_update and not self.pk:
            self.pk = self._id

        super().save(*args, **kwargs)


class ActivityRecommendation(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='recommendations')
    emotion = models.CharField(max_length=50)
    confidence = models.FloatField(default=0.5)
    recommendations = models.JSONField()
    encouragement = models.TextField()
    color = models.CharField(max_length=7, default='#6366f1')
    icon = models.CharField(max_length=50, default='fas fa-lightbulb')
    enriched_content = models.JSONField(null=True, blank=True)
    has_enrichment = models.BooleanField(default=False)
    enrichment_generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Recommandations pour '{self.note.title}' - {self.emotion}"

    def get_multimedia_content(self):
        if self.enriched_content and 'multimedia_content' in self.enriched_content:
            return self.enriched_content['multimedia_content']
        return None

    def get_explanation(self):
        if self.enriched_content and 'explanation' in self.enriched_content:
            return self.enriched_content['explanation']
        return None

    def get_local_suggestions(self):
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

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_affirmations')
    text = models.CharField(max_length=240)
    tone = models.CharField(max_length=32, choices=TONE_CHOICES, default='calm')
    topic = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:60]

