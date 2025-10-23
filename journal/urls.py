from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('base/', views.base, name='base'),
    path('category_management/', views.category_management, name='category_management'),
    path('category/edit/<int:category_id>/', views.edit_category, name='edit_category'),
    path('category/delete/<int:category_id>/', views.delete_category, name='delete_category'),
    path('create_note/', views.create_note, name='create_note'),
    path('notes/<int:note_id>/edit/', views.edit_note, name='edit_note'),
    path('notes/<int:note_id>/delete/', views.delete_note, name='delete_note'),
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
    path('notes/category/<int:category_id>/', views.notes_by_category, name='notes_by_category'),
    path('tag_create/', views.tag_create, name='tag_create'),
    path('event_create/', views.event_create, name='event_create'),
    path('predict/', views.predict_emotion_api, name='predict_emotion'),
    # Goals CRUD
    path('goals/', views.goals_list, name='goals_list'),
    path('goals/create/', views.goal_create, name='goal_create'),
    path('goals/<int:pk>/', views.goal_detail, name='goal_detail'),
    path('goals/<int:pk>/edit/', views.goal_update, name='goal_update'),
    path('goals/<int:pk>/delete/', views.goal_delete, name='goal_delete'),
    path('goals/<int:pk>/toggle_milestone/', views.toggle_milestone, name='toggle_milestone'),

]