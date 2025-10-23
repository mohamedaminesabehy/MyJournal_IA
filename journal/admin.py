from django.contrib import admin
from .models import UserProfile, Category, Note, Goal

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
	list_display = ('title', 'user', 'status', 'priority', 'visibility', 'progress_cached', 'created_at')
	list_filter = ('status', 'priority', 'visibility')
	search_fields = ('title', 'description', 'reward')

admin.site.register(UserProfile)
admin.site.register(Category)
admin.site.register(Note)
