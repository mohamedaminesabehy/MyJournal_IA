from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date
from django.utils.text import slugify


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.username

class Category(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True)
    # Passage à ManyToMany: une catégorie peut appartenir à plusieurs utilisateurs,
    # et un utilisateur peut avoir plusieurs catégories
    users = models.ManyToManyField(User, related_name='categories', blank=True)

    def __str__(self):
        return self.name

class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200)
    content = models.CharField(max_length=5000)
    location = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_draft = models.BooleanField(default=False)
    emotion = models.CharField(max_length=50, blank=True)
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
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    # Cached progress (computed on save) to speed up list rendering
    progress_cached = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

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
        # generate slug from title if not set
        if not self.slug and self.title:
            base = slugify(self.title)[:200]
            slug = base
            counter = 1
            # Ensure uniqueness
            while type(self).objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug

        # update cached progress
        pct = self.progress_pct()
        if pct is not None:
            self.progress_cached = pct

        super().save(*args, **kwargs)