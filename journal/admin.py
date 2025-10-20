from django.contrib import admin
from .models import UserProfile, Category, Note

admin.site.register(UserProfile)
admin.site.register(Category)
admin.site.register(Note)
