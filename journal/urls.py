from django.urls import path
from . import views
from . import views_albums
from . import views_affirmations as av

urlpatterns = [
    path('', views.home, name='home'),
    path('base/', views.base, name='base'),
    path('category_management/', views.category_management, name='category_management'),
    path('create_note/', views.create_note, name='create_note'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Galerie Intelligente
    path('gallery/', views.gallery, name='gallery'),
    path('gallery/upload/', views.media_upload, name='media_upload'),
    path('gallery/<int:media_id>/', views.media_detail, name='media_detail'),
    path('gallery/<int:media_id>/edit/', views.media_edit, name='media_edit'),
    path('gallery/<int:media_id>/delete/', views.media_delete, name='media_delete'),
    path('gallery/<int:media_id>/analyze/', views.media_analyze, name='media_analyze'),
    path('gallery/<int:media_id>/tag/<int:tag_id>/delete/', views.media_delete_tag, name='media_delete_tag'),
    path('smart-albums/', views.smart_albums, name='smart_albums'),
    
    # Albums Intelligents
    path('albums/', views_albums.smart_albums_list, name='smart_albums_list'),
    path('albums/<int:album_id>/', views_albums.album_detail, name='album_detail'),
    path('albums/create-auto/', views_albums.create_auto_albums, name='create_auto_albums'),
    path('albums/create-manual/', views_albums.create_manual_album, name='create_manual_album'),
    path('albums/<int:album_id>/update/', views_albums.update_album, name='update_album'),
    path('albums/<int:album_id>/delete/', views_albums.delete_album, name='delete_album'),
    path('albums/<int:album_id>/add-media/', views_albums.add_media_to_album, name='add_media_to_album'),
    path('albums/<int:album_id>/remove-media/<int:media_id>/', views_albums.remove_media_from_album, name='remove_media_from_album'),
    path('api/albums/suggestions/', views_albums.album_suggestions_json, name='album_suggestions_json'),
    
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
    path('tag_create/', views.tag_create, name='tag_create'),
    path('event_create/', views.event_create, name='event_create'),
    path('notes/category/<int:category_id>/', views.notes_by_category, name='notes_by_category'),
    path('tag_create/', views.tag_create, name='tag_create'),
    path('event_create/', views.event_create, name='event_create'),
    path('predict/', views.predict_emotion_api, name='predict_emotion'),
    # Goals CRUD - Using slug instead of pk for MongoDB compatibility
    path('goals/', views.goals_list, name='goals_list'),
    path('goals/create/', views.goal_create, name='goal_create'),
    path('goals/<slug:slug>/', views.goal_detail, name='goal_detail'),
    path('goals/<slug:slug>/edit/', views.goal_update, name='goal_update'),
    path('goals/<slug:slug>/delete/', views.goal_delete, name='goal_delete'),
    path('goals/<slug:slug>/toggle_milestone/', views.toggle_milestone, name='toggle_milestone'),

    path('notes/<int:note_id>/recommendations/', views.generate_recommendations, name='generate_recommendations'),
    path('notes/<int:note_id>/recommendations/regenerate/', views.regenerate_recommendations, name='regenerate_recommendations'),


    path('affirmations/', av.affirmation_list, name='affirmation_list'),
    path('affirmations/new/', av.affirmation_new, name='affirmation_new'),
    path('affirmations/<int:pk>/edit/', av.affirmation_edit, name='affirmation_edit'),
    path('affirmations/<int:pk>/delete/', av.affirmation_delete, name='affirmation_delete'),
    path('affirmations/<int:pk>/use/', av.affirmation_use, name='affirmation_use'),
    path('affirmations/suggest/', av.affirmation_suggest, name='affirmation_suggest'),
    path("affirmations/suggest/api/", av.affirmation_suggest_api, name="affirmation_suggest_api"),
    path("affirmations/suggest/reroll/", av.affirmation_paraphrase_one, name="affirmation_paraphrase_one"),
]