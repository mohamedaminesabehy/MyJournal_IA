
from django.contrib import admin
from .models import (
    UserProfile,
    Category,
    Note,
    Goal,
    Media,
    MediaAnalysis,
    MediaTag,
    SmartAlbum,
)


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'priority', 'visibility', 'progress_cached', 'created_at')
    list_filter = ('status', 'priority', 'visibility')
    search_fields = ('title', 'description', 'reward')


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'media_type', 'file_size_display', 'is_analyzed', 'uploaded_at')
    list_filter = ('media_type', 'is_analyzed', 'is_favorite', 'uploaded_at')
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('file_size', 'width', 'height', 'uploaded_at', 'updated_at')

    fieldsets = (
        ('Informations de base', {
            'fields': ('user', 'title', 'description', 'media_type')
        }),
        ('Fichier', {
            'fields': ('file', 'thumbnail', 'file_size')
        }),
        ('Métadonnées', {
            'fields': ('width', 'height', 'duration')
        }),
        ('Organisation', {
            'fields': ('category', 'album', 'is_favorite', 'is_analyzed')
        }),
        ('Dates', {
            'fields': ('uploaded_at', 'updated_at')
        }),
    )


@admin.register(MediaAnalysis)
class MediaAnalysisAdmin(admin.ModelAdmin):
    list_display = ('media', 'mood', 'confidence_score', 'vision_api_used', 'analyzed_at')
    list_filter = ('vision_api_used', 'generative_api_used', 'analyzed_at')
    search_fields = ('media__title', 'ai_title', 'ai_description')
    readonly_fields = ('analyzed_at', 'updated_at')

    fieldsets = (
        ('Média', {
            'fields': ('media',)
        }),
        ('Vision AI - Détection', {
            'fields': ('detected_objects', 'detected_locations', 'detected_faces', 'extracted_text')
        }),
        ('Vision AI - Couleurs & Émotions', {
            'fields': ('dominant_colors', 'color_palette', 'detected_emotions', 'mood')
        }),
        ('Generative AI', {
            'fields': ('ai_title', 'ai_description', 'ai_summary')
        }),
        ('Suggestions IA', {
            'fields': ('suggested_tags', 'suggested_filters', 'creative_suggestions')
        }),
        ('Métadonnées', {
            'fields': ('vision_api_used', 'generative_api_used', 'confidence_score', 'analyzed_at', 'updated_at')
        }),
    )


@admin.register(MediaTag)
class MediaTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'media', 'source', 'confidence', 'created_at')
    list_filter = ('source', 'created_at')
    search_fields = ('name', 'media__title')


@admin.register(SmartAlbum)
class SmartAlbumAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'album_type', 'media_count', 'created_at')
    list_filter = ('album_type', 'created_at')
    search_fields = ('name', 'description', 'user__username')
    filter_horizontal = ('media',)

    def media_count(self, obj):
        return obj.media.count()
    media_count.short_description = 'Nombre de médias'


admin.site.register(UserProfile)
admin.site.register(Category)
admin.site.register(Note)
