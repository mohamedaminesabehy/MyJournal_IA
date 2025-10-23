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
