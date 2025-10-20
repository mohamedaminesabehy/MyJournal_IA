from django.db import models
from django.contrib.auth.models import User

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
    users = models.ManyToManyField(User, related_name='categories', blank=True)

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