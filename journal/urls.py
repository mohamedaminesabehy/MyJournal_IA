from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('base/', views.base, name='base'),
    path('category_management/', views.category_management, name='category_management'),
    path('create_note/', views.create_note, name='create_note'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('gallery/', views.gallery, name='gallery'),
    path('hello/', views.hello, name='hello'),
    path('modern_notes/', views.modern_notes, name='modern_notes'),
    path('profile/', views.profile, name='profile'),
    path('signin/', views.signin, name='signin'),
    path('signup/', views.signup, name='signup'),
    path('statistics/', views.statistics, name='statistics'),
    path('tags/', views.tags, name='tags'),
    path('view_notes/', views.view_notes, name='view_notes'),
    path('tag_create/', views.tag_create, name='tag_create'),
    path('event_create/', views.event_create, name='event_create'),
]