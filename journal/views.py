from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
import re
import json
import logging
import traceback
import os
import threading
from datetime import datetime, date, time, timedelta

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django import forms

from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods, require_POST

# Import conditionnel pour éviter les erreurs si cv2 n'est pas installé
try:
    from .services.vision_service import analyze_media_vision
except ImportError:
    analyze_media_vision = None

from .forms import (
    CustomUserCreationForm,
    MediaUploadForm,
    MultipleMediaUploadForm,
    MediaEditForm,
    GalleryFilterForm,
    MediaTagForm,
    NoteForm,
    GoalForm,
)

from .models import (
    UserProfile,
    Category,
    Media,
    MediaAnalysis,
    MediaTag,
    SmartAlbum,
    Note,
    Goal,
    ActivityRecommendation,
)

from .utils import (
    lr_model,
    clean_text,
    predict_emotion,
    predict_goal_duration,
    generate_motivation_message,
)


from .recommendation_engine import recommendation_engine
from .perplexity_service import perplexity_service

from django.conf import settings
from pymongo import MongoClient
from bson import ObjectId

from PIL import Image

logger = logging.getLogger(__name__)


def _to_bson_datetime(value):
    """Convert date or naive datetime to a BSON-compatible datetime.

    - If value is a datetime, return as-is.
    - If value is a date (no time), combine with time.min to create a datetime.
    - Try to make it timezone-aware if Django timezone utilities are available.
    - If None or other types, return as-is (caller must handle validation).
    """
    if value is None:
        return None
    # If already a datetime, return it
    if isinstance(value, datetime):
        return value
    # If it's a date (no time part), combine with midnight
    if isinstance(value, date):
        dt = datetime.combine(value, time.min)
        try:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
        except Exception:
            # If timezone utilities fail for any reason, fall back to naive datetime
            pass
        return dt
    return value


@login_required
def create_note(request):
    if request.method == 'POST':
        form = NoteForm(request.POST, user=request.user)
        is_draft = 'is_draft' in request.POST
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.is_draft = is_draft
            # Remove <p> and </p> tags from content before saving
            raw_content = form.cleaned_data.get('content', '')
            note.content = re.sub(r'</?p>', '', raw_content)
            
            # Predict emotion for the note content
            if lr_model and note.content:
                try:
                    emotion, confidence = predict_emotion(note.content, lr_model)
                    if emotion:
                        note.emotion = emotion
                        note.emotion_confidence = float(confidence * 100)
                except Exception as e:
                    print(f"Error predicting emotion: {e}")
            
            # If the form returned a numeric PK for category (ChoiceField fallback),
            # assign it to category_id so the FK is set correctly.
            cat_val = form.cleaned_data.get('category')
            try:
                if isinstance(cat_val, int):
                    note.category_id = cat_val
                elif isinstance(cat_val, str) and cat_val.isdigit():
                    note.category_id = int(cat_val)
            except Exception:
                # ignore and let save fail if invalid
                pass

            note.save()
            return redirect('view_notes')
        else:
            print(f"Form validation errors for create_note: {form.errors}")
    else:
        form = NoteForm(user=request.user)
    return render(request, 'create_note.html', {'form': form})


@login_required
def edit_note(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        category_id = request.POST.get('category_id')
        # Remove <p> and </p> tags from content before saving
        content = re.sub(r'</?p>', '', content)
        if title and content:
            note.title = title
            note.content = content
            
            # Predict emotion for the updated content
            if lr_model and note.content:
                try:
                    emotion, confidence = predict_emotion(note.content, lr_model)
                    if emotion:
                        note.emotion = emotion
                        note.emotion_confidence = float(confidence * 100)
                except Exception as e:
                    print(f"Error predicting emotion: {e}")
            
            note.save()
            if category_id:
                return redirect('notes_by_category', category_id=int(category_id))
            return redirect('view_notes')
        else:
            # Re-render notes list with an error message (simple approach)
            categories = Category.objects.filter(users=request.user)
            notes = Note.objects.filter(user=request.user).order_by('-created_at')
            context = {
                'categories': categories,
                'notes': notes,
                'error': 'Le titre et le contenu sont requis pour la modification.'
            }
            return render(request, 'view_notes.html', context)
    return redirect('view_notes')


@login_required
def delete_note(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        note.delete()
        if category_id:
            return redirect('notes_by_category', category_id=int(category_id))
        return redirect('view_notes')
    return redirect('view_notes')

def home(request):
    return render(request, 'home.html')


@login_required
def base(request):
    return render(request, 'base.html')


@login_required
def dashboard(request):
    """Dashboard simplifié compatible Djongo/MongoDB"""
    from collections import Counter
    import datetime
    from datetime import timedelta
    
    try:
        # Récupérer les notes de l'utilisateur
        user_notes = list(Note.objects.filter(user=request.user))
        total_notes = len(user_notes)
        
        # Calcul simple sans requêtes complexes
        emotion_scores = {'joy': 5, 'love': 5, 'surprise': 4, 'sadness': 2, 'fear': 2, 'anger': 1}
        
        # Statistiques basiques
        notes_with_emotion = [n for n in user_notes if n.emotion]
        if notes_with_emotion:
            total_score = sum(emotion_scores.get(n.emotion, 3) for n in notes_with_emotion)
            average_mood_score = round(total_score / len(notes_with_emotion), 1) if notes_with_emotion else 0
            
            if average_mood_score >= 4:
                average_mood, mood_color = "Très Positive", "success"
            elif average_mood_score >= 3:
                average_mood, mood_color = "Positive", "info"
            elif average_mood_score >= 2:
                average_mood, mood_color = "Neutre", "warning"
            else:
                average_mood, mood_color = "Négative", "danger"
                
            emotion_distribution = Counter(n.emotion for n in notes_with_emotion)
        else:
            average_mood, mood_color, average_mood_score = "Non définie", "secondary", 0
            emotion_distribution = Counter()
        
        # Notes récentes
        recent_notes = sorted(user_notes, key=lambda x: x.created_at, reverse=True)[:5]
        
        # Streak simple
        current_streak = 0
        today = datetime.date.today()
        for i in range(30):  # Vérifier 30 derniers jours max
            check_date = today - timedelta(days=i)
            if any(n.created_at.date() == check_date for n in user_notes):
                current_streak += 1
            elif i == 0:  # Si pas de note aujourd'hui, continuer
                continue
            else:
                break
        
        # Données pour graphiques (simplifiées)
        mood_chart_data = [None] * 7
        mood_chart_labels = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            day_notes = [n for n in notes_with_emotion if n.created_at.date() == date]
            if day_notes:
                day_score = sum(emotion_scores.get(n.emotion, 3) for n in day_notes) / len(day_notes)
                mood_chart_data[6-i] = round(day_score, 1)
            mood_chart_labels.append(date.strftime('%d/%m'))
        
        # Distribution des émotions en pourcentage
        emotion_chart_data = []
        emotion_chart_labels = []
        emotion_chart_colors = []
        color_map = {'joy': '#fbbf24', 'love': '#ef4444', 'surprise': '#3b82f6',
                    'sadness': '#6366f1', 'fear': '#6b7280', 'anger': '#dc2626'}
        emotion_names = {'joy': 'Joie', 'love': 'Amour', 'surprise': 'Surprise',
                        'sadness': 'Tristesse', 'fear': 'Peur', 'anger': 'Colère'}
        
        if emotion_distribution:
            total = sum(emotion_distribution.values())
            for emotion, count in emotion_distribution.most_common():
                emotion_chart_data.append(round(count / total * 100, 1))
                emotion_chart_labels.append(emotion_names.get(emotion, emotion))
                emotion_chart_colors.append(color_map.get(emotion, '#6b7280'))
        
        # Recommandations - Calcul par jour
        all_recommendations = list(ActivityRecommendation.objects.filter(note__user=request.user))
        total_recommendations = len(all_recommendations)
        recommendations_chart_data = []
        recommendations_chart_labels = []
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            # Compter les recommandations créées ce jour
            day_recommendations = sum(1 for rec in all_recommendations if rec.created_at.date() == date)
            recommendations_chart_data.append(day_recommendations)
            
            # Noms des jours en français avec date
            day_names = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
            day_label = f"{day_names[date.weekday()]} {date.strftime('%d/%m')}"
            recommendations_chart_labels.append(day_label)
        
        print(f"DEBUG Dashboard - Total recommendations: {total_recommendations}")
        print(f"DEBUG Dashboard - Recommendations by day: {recommendations_chart_data}")
        print(f"DEBUG Dashboard - Labels: {recommendations_chart_labels}")
        
        # Compter le nombre de médias de l'utilisateur
        try:
            total_media = Media.objects.filter(user=request.user).count()
        except Exception as e:
            print(f"⚠️ Erreur lors du comptage des médias: {e}")
            total_media = 0
        
        context = {
            'total_notes': total_notes,
            'average_mood': average_mood,
            'mood_color': mood_color,
            'average_mood_score': average_mood_score,
            'current_streak': current_streak,
            'recent_notes': recent_notes,
            'mood_chart_data': json.dumps(mood_chart_data),
            'mood_chart_labels': json.dumps(mood_chart_labels),
            'emotion_chart_data': json.dumps(emotion_chart_data),
            'emotion_chart_labels': json.dumps(emotion_chart_labels),
            'emotion_chart_colors': json.dumps(emotion_chart_colors),
            'emotion_distribution': dict(emotion_distribution),
            'recommendations_chart_data': json.dumps(recommendations_chart_data),
            'recommendations_chart_labels': json.dumps(recommendations_chart_labels),
            'total_recommendations': total_recommendations,
            'total_media': total_media,
        }
        
        return render(request, 'dashboard.html', context)
        
    except Exception as e:
        print(f"❌ Erreur dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        # Fallback: dashboard vide
        return render(request, 'dashboard.html', {
            'total_notes': 0,
            'average_mood': 'Non définie',
            'mood_color': 'secondary',
            'average_mood_score': 0,
            'current_streak': 0,
            'recent_notes': [],
            'mood_chart_data': '[]',
            'mood_chart_labels': '[]',
            'emotion_chart_data': '[]',
            'emotion_chart_labels': '[]',
            'emotion_chart_colors': '[]',
            'emotion_distribution': {},
            'recommendations_chart_data': '[]',
            'recommendations_chart_labels': '[]',
            'total_recommendations': 0,
            'total_media': 0,
        })



@login_required
def category_management(request):
    if request.method == 'POST':
        category_name = (request.POST.get('categoryName') or '').strip()
        category_icon = request.POST.get('categoryIcon')
        if category_name:
            try:
                # Solution pour contourner les problèmes de validation Djongo avec ForeignKey
                from pymongo import MongoClient
                from bson import ObjectId
                from django.conf import settings
                
                # Connexion directe à MongoDB
                mongo_uri = settings.DATABASES['default']['CLIENT']['host']
                client = MongoClient(mongo_uri)
                db = client['journalDB']
                collection = db['journal_category']
                
                # Générer un nouvel ID unique pour Djongo
                # Trouver le max ID existant et ajouter 1
                max_doc = collection.find_one(sort=[('id', -1)])
                next_id = (max_doc['id'] + 1) if max_doc and 'id' in max_doc and max_doc['id'] is not None else 1
                
                # Créer le document MongoDB avec un champ 'id' pour Djongo
                # On stocke à la fois 'user_id' (scalar) et 'users' (liste) pour compatibilité
                category_doc = {
                    'id': next_id,
                    'name': category_name,
                    'icon': category_icon or '',
                    'user_id': request.user.id,  # Stocker l'ID de l'utilisateur (index unique attendu)
                    'users': [request.user.id],  # Ancienne shape utilisée ailleurs dans le code
                }

                # Insertet en gérant les doublons explicitement pour renvoyer un message clair
                from pymongo.errors import DuplicateKeyError
                try:
                    result = collection.insert_one(category_doc)
                except DuplicateKeyError as dk:
                    client.close()
                    return JsonResponse({'success': False, 'error': 'Une catégorie avec ce nom existe déjà.'})
                category_id = str(next_id)  # Utiliser l'ID numérique, pas l'ObjectId
                
                client.close()  # Fermer la connexion
                
                return JsonResponse({
                    'success': True, 
                    'category': {
                        'id': category_id, 
                        'name': category_name, 
                        'icon': category_icon or ''
                    }
                })
            except Exception as e:
                import traceback
                import sys
                error_details = traceback.format_exc()
                print(f"❌ Erreur création catégorie: {error_details}", file=sys.stderr)
                print(f"❌ Type d'erreur: {type(e).__name__}", file=sys.stderr)
                print(f"❌ Message: {str(e)}", file=sys.stderr)
                error_message = str(e) if str(e) else f"Erreur de type {type(e).__name__}"
                return JsonResponse({'success': False, 'error': f'Erreur: {error_message}'})
        return JsonResponse({'success': False, 'error': 'Le nom de la catégorie est requis.'})
    
    try:
        # Charger les catégories directement depuis MongoDB pour couvrir les cas
        # où les documents sont présents uniquement dans la collection Mongo
        from pymongo import MongoClient
        from django.conf import settings

        mongo_uri = settings.DATABASES['default']['CLIENT']['host']
        client = MongoClient(mongo_uri)
        db = client['journalDB']
        collection = db['journal_category']

        # Chercher par user_id scalar ou présence dans le tableau 'users'
        user_categories_data = list(collection.find({'$or': [{'user_id': request.user.id}, {'users': request.user.id}]}))
        client.close()

        # Convertir en objets simples pour le template (compatibilité avec ORM objects)
        categories = []
        for cat_data in user_categories_data:
            class CategoryProxy:
                def __init__(self, data):
                    # Djongo-compatible numeric 'id' may be stored in 'id' field
                    self.id = data.get('id') or data.get('_id')
                    self.name = data.get('name', '')
                    self.icon = data.get('icon', '')
                    # Expose user_id for debugging/compat
                    self.user_id = data.get('user_id')
            categories.append(CategoryProxy(cat_data))
    except Exception as e:
        print(f"❌ Erreur récupération catégories: {str(e)}")
        categories = []
    
    return render(request, 'category_management.html', {'categories': categories})


@login_required
def edit_category(request, category_id):
    if request.method == 'POST':
        category_name = (request.POST.get('categoryName') or '').strip()
        category_icon = request.POST.get('categoryIcon')
        if category_name:
            try:
                # Modification directe avec PyMongo
                from pymongo import MongoClient
                from django.conf import settings
                
                mongo_uri = settings.DATABASES['default']['CLIENT']['host']
                client = MongoClient(mongo_uri)
                db = client['journalDB']
                collection = db['journal_category']
                
                # Vérifier que la catégorie appartient bien à l'utilisateur
                # Supporter les deux shapes: scalar 'user_id' ou liste 'users'
                category = collection.find_one({'id': int(category_id), 'user_id': request.user.id})
                used_filter = None
                if category:
                    used_filter = {'id': int(category_id), 'user_id': request.user.id}
                else:
                    category = collection.find_one({'id': int(category_id), 'users': request.user.id})
                    if category:
                        used_filter = {'id': int(category_id), 'users': request.user.id}

                if not category:
                    client.close()
                    return JsonResponse({'success': False, 'error': 'Catégorie non trouvée'})

                # Mettre à jour la catégorie (mettre à jour les deux champs si possible)
                update_payload = {'$set': {'name': category_name, 'icon': category_icon or ''}}
                collection.update_one(used_filter, update_payload)
                
                client.close()
                
                return JsonResponse({
                    'success': True, 
                    'category': {
                        'id': category_id, 
                        'name': category_name, 
                        'icon': category_icon or ''
                    }
                })
            except Exception as e:
                import traceback
                print(f"❌ Erreur modification catégorie: {traceback.format_exc()}")
                return JsonResponse({'success': False, 'error': str(e) or 'Erreur lors de la modification'})
        return JsonResponse({'success': False, 'error': 'Le nom de la catégorie est requis.'})
    return JsonResponse({'success': False, 'error': 'Méthode invalide.'})

@login_required
def delete_category(request, category_id):
    if request.method == 'POST':
        try:
            # Suppression directe avec PyMongo
            from pymongo import MongoClient
            from django.conf import settings
            
            mongo_uri = settings.DATABASES['default']['CLIENT']['host']
            client = MongoClient(mongo_uri)
            db = client['journalDB']
            collection = db['journal_category']
            
            # Vérifier que la catégorie appartient bien à l'utilisateur avant suppression
            # Essayer suppression par 'user_id' puis par 'users' pour compatibilité
            result = collection.delete_one({'id': int(category_id), 'user_id': request.user.id})
            if result.deleted_count == 0:
                result = collection.delete_one({'id': int(category_id), 'users': request.user.id})
            
            client.close()
            
            if result.deleted_count > 0:
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Catégorie non trouvée ou non autorisée'})
                
        except Exception as e:
            import traceback
            print(f"❌ Erreur suppression catégorie: {traceback.format_exc()}")
            return JsonResponse({'success': False, 'error': str(e) or 'Erreur lors de la suppression'})
    return JsonResponse({'success': False, 'error': 'Méthode invalide.'})


@login_required  
def dashboard_OLD_BACKUP(request):
    from django.db.models import Count, Avg
    from collections import Counter
    import datetime
    from datetime import timedelta
    
    # Récupérer toutes les notes de l'utilisateur
    user_notes = Note.objects.filter(user=request.user)
    
    # Statistiques de base
    total_notes = user_notes.count()
    
    # Calcul de l'humeur moyenne basée sur les émotions (amélioré)
    emotion_scores = {
        'joy': 5,      # Joie - Très positif
        'love': 5,     # Amour - Très positif
        'surprise': 4, # Surprise - Positif
        'sadness': 2,  # Tristesse - Négatif
        'fear': 2,     # Peur - Négatif
        'anger': 1     # Colère - Très négatif
    }
    
    # Traductions des émotions pour l'affichage
    emotion_translations = {
        'joy': 'Joie',
        'love': 'Amour',
        'surprise': 'Surprise',
        'sadness': 'Tristesse',
        'fear': 'Peur',
        'anger': 'Colère'
    }
    
    notes_with_emotion = user_notes.filter(emotion__isnull=False)
    if notes_with_emotion.exists():
        total_score = 0
        emotion_count = 0
        emotion_distribution = Counter()
        
        for note in notes_with_emotion:
            if note.emotion in emotion_scores:
                total_score += emotion_scores[note.emotion]
                emotion_count += 1
                emotion_distribution[note.emotion] += 1
        
        if emotion_count > 0:
            average_mood_score = round(total_score / emotion_count, 1)
            
            # Classification plus précise de l'humeur
            if average_mood_score >= 4.7:
                average_mood = "Excellente"
                mood_color = "success"
            elif average_mood_score >= 4.0:
                average_mood = "Très Positive"
                mood_color = "success"
            elif average_mood_score >= 3.5:
                average_mood = "Positive"
                mood_color = "success"
            elif average_mood_score >= 2.8:
                average_mood = "Plutôt Positive"
                mood_color = "info"
            elif average_mood_score >= 2.2:
                average_mood = "Neutre"
                mood_color = "warning"
            elif average_mood_score >= 1.8:
                average_mood = "Plutôt Négative"
                mood_color = "warning"
            elif average_mood_score >= 1.3:
                average_mood = "Négative"
                mood_color = "danger"
            else:
                average_mood = "Très Négative"
                mood_color = "danger"
        else:
            average_mood = "Non définie"
            mood_color = "secondary"
            average_mood_score = 0
    else:
        average_mood = "Non définie"
        mood_color = "secondary"
        average_mood_score = 0
        emotion_distribution = Counter()
    
    # Données pour le graphique de l'humeur (7 derniers jours) - Compatible MongoDB
    today = datetime.date.today()
    mood_chart_data = []
    mood_chart_labels = []
    
    for i in range(6, -1, -1):  # 7 jours en arrière
        date = today - timedelta(days=i)
        # Utiliser des filtres de plage de dates compatibles avec MongoDB
        start_datetime = datetime.datetime.combine(date, datetime.time.min)
        end_datetime = datetime.datetime.combine(date, datetime.time.max)
        # Rendre aware si naïf pour éviter RuntimeWarning
        start_datetime = timezone.make_aware(start_datetime) if timezone.is_naive(start_datetime) else start_datetime
        end_datetime = timezone.make_aware(end_datetime) if timezone.is_naive(end_datetime) else end_datetime
        
        day_notes = user_notes.filter(
            created_at__gte=start_datetime,
            created_at__lte=end_datetime,
            emotion__isnull=False
        )
        
        if day_notes.exists():
            day_total_score = 0
            day_count = 0
            for note in day_notes:
                if note.emotion in emotion_scores:
                    day_total_score += emotion_scores[note.emotion]
                    day_count += 1
            
            if day_count > 0:
                day_average = round(day_total_score / day_count, 1)
            else:
                day_average = None  # Pas de données pour ce jour
        else:
            day_average = None  # Pas de données pour ce jour
        
        mood_chart_data.append(day_average)
        
        # Noms des jours en français avec date
        day_names = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
        day_label = f"{day_names[date.weekday()]} {date.strftime('%d/%m')}"
        mood_chart_labels.append(day_label)
    
    # Calcul de la séquence actuelle (jours consécutifs avec des entrées) - Compatible MongoDB
    current_streak = 0
    check_date = today
    while True:
        start_datetime = datetime.datetime.combine(check_date, datetime.time.min)
        end_datetime = datetime.datetime.combine(check_date, datetime.time.max)
        # Rendre aware si naïf pour éviter RuntimeWarning
        start_datetime = timezone.make_aware(start_datetime) if timezone.is_naive(start_datetime) else start_datetime
        end_datetime = timezone.make_aware(end_datetime) if timezone.is_naive(end_datetime) else end_datetime
        
        if user_notes.filter(created_at__gte=start_datetime, created_at__lte=end_datetime).exists():
            current_streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    
    # Notes récentes (5 dernièmes)
    recent_notes = user_notes.order_by('-created_at')[:5]
    
    # Préparer les données pour le graphique en pourcentages
    emotion_chart_data = []
    emotion_chart_labels = []
    emotion_chart_colors = []
    
    color_map = {
        'joy': '#fbbf24',      # jaune
        'love': '#ef4444',     # rouge
        'surprise': '#3b82f6', # bleu
        'sadness': '#6366f1',  # indigo
        'fear': '#6b7280',     # gris
        'anger': '#dc2626'     # rouge foncé
    }
    
    if emotion_distribution:
        total_emotions = sum(emotion_distribution.values())
        for emotion, count in emotion_distribution.most_common():
            percentage = (count / total_emotions) * 100
            emotion_chart_data.append(round(percentage, 1))
            
            # Traduction des émotions
            emotion_translations = {
                'joy': 'Joie',
                'love': 'Amour', 
                'surprise': 'Surprise',
                'sadness': 'Tristesse',
                'fear': 'Peur',
                'anger': 'Colère'
            }
            emotion_chart_labels.append(emotion_translations.get(emotion, emotion))
            emotion_chart_colors.append(color_map.get(emotion, '#6b7280'))
    
    # Données pour le graphique des recommandations (7 derniers jours)
    recommendations_chart_data = []
    recommendations_chart_labels = []
    
    for i in range(6, -1, -1):  # 7 jours en arrière
        date = today - timedelta(days=i)
        start_datetime = datetime.datetime.combine(date, datetime.time.min)
        end_datetime = datetime.datetime.combine(date, datetime.time.max)
        # Rendre aware si naïf pour éviter RuntimeWarning
        start_datetime = timezone.make_aware(start_datetime) if timezone.is_naive(start_datetime) else start_datetime
        end_datetime = timezone.make_aware(end_datetime) if timezone.is_naive(end_datetime) else end_datetime
        
        # Compter les recommandations générées pour ce jour
        day_recommendations = ActivityRecommendation.objects.filter(
            note__user=request.user,
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).count()
        
        recommendations_chart_data.append(day_recommendations)
        
        # Noms des jours en français avec date
        day_names = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
        day_label = f"{day_names[date.weekday()]} {date.strftime('%d/%m')}"
        recommendations_chart_labels.append(day_label)
    
    # Statistiques des recommandations
    total_recommendations = ActivityRecommendation.objects.filter(note__user=request.user).count()
    
    # Debug pour voir les données
    print(f"DEBUG - Recommendations chart data: {recommendations_chart_data}")
    print(f"DEBUG - Recommendations chart labels: {recommendations_chart_labels}")
    print(f"DEBUG - Total recommendations: {total_recommendations}")
    
    context = {
        'total_notes': total_notes,
        'average_mood': average_mood,
        'mood_color': mood_color,
        'average_mood_score': round(average_mood_score, 1),
        'current_streak': current_streak,
        'recent_notes': recent_notes,
        'mood_chart_data': json.dumps(mood_chart_data),
        'mood_chart_labels': json.dumps(mood_chart_labels),
        'emotion_chart_data': json.dumps(emotion_chart_data),
        'emotion_chart_labels': json.dumps(emotion_chart_labels),
        'emotion_chart_colors': json.dumps(emotion_chart_colors),
        'emotion_distribution': dict(emotion_distribution),
        'recommendations_chart_data': json.dumps(recommendations_chart_data),
        'recommendations_chart_labels': json.dumps(recommendations_chart_labels),
        'total_recommendations': total_recommendations,
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def gallery(request):
    return render(request, 'gallery.html')

@login_required
def hello(request):
    return render(request, 'hello.html')

@login_required
def modern_notes(request):
    return render(request, 'modern_notes.html')

@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'profile.html', {'user_profile': user_profile})


@login_required
def goals_list(request):
    client = MongoClient(settings.DATABASES['default']['CLIENT']['host'])
    db = client[settings.DATABASES['default']['NAME']]
    collection = db['journal_goal']

    goals_data = list(collection.find({'user_id': request.user.id}).sort('created_at', -1))
    goals = []
    for goal_data in goals_data:
        milestones = goal_data.get('milestones', [])
        if isinstance(milestones, str):
            try:
                milestones = json.loads(milestones)
            except Exception:
                milestones = []
        if not isinstance(milestones, list):
            milestones = []

        goal = Goal(
            id=goal_data.get('_id'),
            user=request.user,
            title=goal_data.get('title', ''),
            description=goal_data.get('description', ''),
            start_date=goal_data.get('start_date'),
            end_date=goal_data.get('end_date'),
            status=goal_data.get('status', Goal.STATUS_ONGOING),
            motivation_level=goal_data.get('motivation_level', 5),
            priority=goal_data.get('priority', Goal.PRIORITY_MEDIUM),
            difficulty=goal_data.get('difficulty', 3),
            reward=goal_data.get('reward', ''),
            recurrence=goal_data.get('recurrence', ''),
            milestones=milestones,
            slug=goal_data.get('slug', ''),
            progress_cached=goal_data.get('progress_cached', 0),
        )
        try:
            goal.ai_motivation = generate_motivation_message(goal, request.user)
        except Exception:
            logger.exception('Failed to generate AI motivation for goal %s', goal.title)
            goal.ai_motivation = None
        goals.append(goal)

    client.close()
    return render(request, 'goals/list.html', {'goals': goals})


@login_required
def goal_detail(request, slug):
    client = MongoClient(settings.DATABASES['default']['CLIENT']['host'])
    db = client[settings.DATABASES['default']['NAME']]
    collection = db['journal_goal']

    goal_data = collection.find_one({'slug': slug, 'user_id': request.user.id})
    if not goal_data:
        client.close()
        raise Http404("Objectif non trouvé")

    milestones = goal_data.get('milestones', [])
    if isinstance(milestones, str):
        try:
            milestones = json.loads(milestones)
        except Exception:
            milestones = []
    if not isinstance(milestones, list):
        milestones = []

    goal = Goal(
        id=goal_data.get('_id'),
        user=request.user,
        title=goal_data.get('title', ''),
        description=goal_data.get('description', ''),
        start_date=goal_data.get('start_date'),
        end_date=goal_data.get('end_date'),
        status=goal_data.get('status', Goal.STATUS_ONGOING),
        motivation_level=goal_data.get('motivation_level', 5),
        priority=goal_data.get('priority', Goal.PRIORITY_MEDIUM),
        difficulty=goal_data.get('difficulty', 3),
        reward=goal_data.get('reward', ''),
        recurrence=goal_data.get('recurrence', ''),
        milestones=milestones,
        slug=goal_data.get('slug', ''),
        progress_cached=goal_data.get('progress_cached', 0),
    )

    duration_min, duration_max, complexity = predict_goal_duration(goal)
    motivation_data = generate_motivation_message(goal, request.user)

    context = {
        'goal': goal,
        'duration_min': duration_min,
        'duration_max': duration_max,
        'complexity': complexity,
        'motivation': motivation_data,
    }

    client.close()
    return render(request, 'goals/detail.html', context)


@login_required
def goal_create(request):
    if request.method == 'POST':
        form = GoalForm(request.POST, user=request.user)
        try:
            logger.info('Posted milestones raw: %s', request.POST.get('milestones'))
        except Exception:
            pass
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            form.save_m2m()
            return redirect('goals_list')
        else:
            logger.warning('Goal create form invalid: %s', form.errors.as_json())
    else:
        form = GoalForm(user=request.user)
    return render(request, 'goals/form.html', {'form': form, 'creating': True})


@login_required
def goal_update(request, slug):
    client = MongoClient(settings.DATABASES['default']['CLIENT']['host'])
    db = client[settings.DATABASES['default']['NAME']]
    collection = db['journal_goal']

    goal_data = collection.find_one({'slug': slug, 'user_id': request.user.id})
    if not goal_data:
        client.close()
        raise Http404("Objectif non trouvé")

    milestones = goal_data.get('milestones', [])
    if isinstance(milestones, str):
        try:
            milestones = json.loads(milestones)
        except Exception:
            milestones = []
    if not isinstance(milestones, list):
        milestones = []

    goal = Goal(
        id=goal_data.get('_id'),
        user=request.user,
        title=goal_data.get('title', ''),
        description=goal_data.get('description', ''),
        start_date=goal_data.get('start_date'),
        end_date=goal_data.get('end_date'),
        status=goal_data.get('status', Goal.STATUS_ONGOING),
        motivation_level=goal_data.get('motivation_level', 5),
        priority=goal_data.get('priority', Goal.PRIORITY_MEDIUM),
        difficulty=goal_data.get('difficulty', 3),
        reward=goal_data.get('reward', ''),
        recurrence=goal_data.get('recurrence', ''),
        milestones=milestones,
        slug=goal_data.get('slug', ''),
        progress_cached=goal_data.get('progress_cached', 0),
    )

    if request.method == 'POST':
        form = GoalForm(request.POST, user=request.user)
        if form.is_valid():
            milestones = form.cleaned_data.get('milestones', [])
            if isinstance(milestones, list) and len(milestones) > 0:
                total = len(milestones)
                done_count = sum(1 for m in milestones if isinstance(m, dict) and m.get('done'))
                progress = int((done_count / total) * 100)
            else:
                progress = 0

            # Convert date objects to BSON-compatible datetimes before sending to PyMongo
            start_date_val = _to_bson_datetime(form.cleaned_data.get('start_date'))
            end_date_val = _to_bson_datetime(form.cleaned_data.get('end_date'))

            result = collection.update_one({'slug': slug, 'user_id': request.user.id}, {'$set': {
                'title': form.cleaned_data['title'],
                'description': form.cleaned_data.get('description', ''),
                'status': form.cleaned_data['status'],
                'start_date': start_date_val,
                'end_date': end_date_val,
                'priority': form.cleaned_data.get('priority', Goal.PRIORITY_MEDIUM),
                'difficulty': form.cleaned_data.get('difficulty', 3),
                'reward': form.cleaned_data.get('reward', ''),
                'recurrence': form.cleaned_data.get('recurrence', ''),
                'motivation_level': form.cleaned_data.get('motivation_level', 5),
                'milestones': milestones,
                'category_id': form.cleaned_data.get('category').id if form.cleaned_data.get('category') else None,
                'progress_cached': progress
            }})

            client.close()
            if result.modified_count > 0:
                return redirect('goal_detail', slug=slug)
            else:
                logger.warning('No document updated for slug: %s', slug)
        else:
            logger.warning('Goal update form invalid: %s', form.errors.as_json())
    else:
        form = GoalForm(instance=goal, user=request.user)

    client.close()
    return render(request, 'goals/form.html', {'form': form, 'creating': False, 'goal': goal})


@login_required
def goal_delete(request, slug):
    client = MongoClient(settings.DATABASES['default']['CLIENT']['host'])
    db = client[settings.DATABASES['default']['NAME']]
    collection = db['journal_goal']

    goal_data = collection.find_one({'slug': slug, 'user_id': request.user.id})
    if not goal_data:
        client.close()
        raise Http404("Objectif non trouvé")

    goal = Goal(id=goal_data.get('_id'), user=request.user, title=goal_data.get('title', ''), description=goal_data.get('description', ''), slug=goal_data.get('slug', ''))

    if request.method == 'POST':
        result = collection.delete_one({'slug': slug, 'user_id': request.user.id})
        client.close()
        if result.deleted_count > 0:
            return redirect('goals_list')
        else:
            logger.warning('No document deleted for slug: %s', slug)
    client.close()
    return render(request, 'goals/confirm_delete.html', {'goal': goal})
 

@csrf_protect
@login_required
@require_POST
def toggle_milestone(request, slug):
    try:
        data = json.loads(request.body.decode('utf-8'))
        idx = int(data.get('index', -1))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Invalid payload'}, status=400)

    client = MongoClient(settings.DATABASES['default']['CLIENT']['host'])
    db = client[settings.DATABASES['default']['NAME']]
    collection = db['journal_goal']

    goal_data = collection.find_one({'slug': slug, 'user_id': request.user.id})
    if not goal_data:
        client.close()
        return JsonResponse({'ok': False, 'error': 'Objectif non trouvé'}, status=404)

    milestones = goal_data.get('milestones', [])
    if isinstance(milestones, str):
        try:
            milestones = json.loads(milestones)
        except Exception:
            milestones = []
    if not isinstance(milestones, list):
        milestones = []

    if idx < 0 or idx >= len(milestones):
        client.close()
        return JsonResponse({'ok': False, 'error': 'Invalid index'}, status=400)

    current = bool(milestones[idx].get('done'))
    new_done = not current

    total = len(milestones)
    done_count = sum(1 for i, m in enumerate(milestones) if (i == idx and new_done) or (i != idx and m.get('done')))
    progress = int((done_count / total) * 100) if total > 0 else 0

    current_status = goal_data.get('status', Goal.STATUS_ONGOING)
    new_status = current_status
    if total > 0 and done_count == total:
        new_status = Goal.STATUS_COMPLETED
    elif current_status == Goal.STATUS_COMPLETED and done_count < total:
        new_status = Goal.STATUS_ONGOING

    try:
        for i, m in enumerate(milestones):
            if not isinstance(m, dict):
                milestones[i] = {'title': str(m), 'done': False}

        milestones[idx]['done'] = bool(new_done)

        result = collection.update_one({'slug': slug, 'user_id': request.user.id}, {'$set': {'milestones': milestones, 'progress_cached': progress, 'status': new_status}})
        client.close()

        if result.modified_count == 0:
            logger.warning('No document updated in toggle_milestone for slug: %s', slug)
            return JsonResponse({'ok': False, 'error': 'Update failed'}, status=500)

        return JsonResponse({'ok': True, 'done': new_done, 'progress': progress, 'status': new_status})
    except Exception as e:
        logger.exception('Error updating milestone for slug %s: %s', slug, e)
        client.close()
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
def gallery(request):
    """Vue principale de la galerie avec filtres et recherche"""
    try:
        media_list = Media.objects.filter(user=request.user)
    except Exception as e:
        logger.exception('Erreur récupération médias: %s', e)
        media_list = Media.objects.none()

    filter_form = GalleryFilterForm(user=request.user, data=request.GET or None)
    if filter_form.is_valid():
        search_query = filter_form.cleaned_data.get('search')
        if search_query:
            media_list = media_list.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query) | Q(tags__name__icontains=search_query)).distinct()

        media_type = filter_form.cleaned_data.get('media_type')
        if media_type:
            media_list = media_list.filter(media_type=media_type)

        category = filter_form.cleaned_data.get('category')
        if category:
            media_list = media_list.filter(category=category)

        is_favorite = filter_form.cleaned_data.get('is_favorite')
        if is_favorite:
            media_list = media_list.filter(is_favorite=True)

        is_analyzed = filter_form.cleaned_data.get('is_analyzed')
        if is_analyzed:
            media_list = media_list.filter(is_analyzed=True)

        sort_by = filter_form.cleaned_data.get('sort_by') or '-uploaded_at'
        media_list = media_list.order_by(sort_by)
    else:
        media_list = media_list.order_by('-uploaded_at')

    try:
        stats = {
            'total_media': Media.objects.filter(user=request.user).count(),
            'total_images': Media.objects.filter(user=request.user, media_type='image').count(),
            'total_videos': Media.objects.filter(user=request.user, media_type='video').count(),
            'total_analyzed': Media.objects.filter(user=request.user, is_analyzed=True).count(),
            'total_favorites': Media.objects.filter(user=request.user, is_favorite=True).count(),
        }
    except Exception as e:
        logger.exception('Erreur stats: %s', e)
        stats = {'total_media': 0, 'total_images': 0, 'total_videos': 0, 'total_analyzed': 0, 'total_favorites': 0}

    paginator = Paginator(media_list, 12)
    page_number = request.GET.get('page')
    media_page = paginator.get_page(page_number)

    context = {'media_list': media_page, 'filter_form': filter_form, 'stats': stats, 'view_mode': request.GET.get('view', 'grid')}
    return render(request, 'gallery.html', context)


@login_required
def hello(request):
    return render(request, 'hello.html')


@login_required
def modern_notes(request):
    return render(request, 'modern_notes.html')


@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'profile.html', {'user_profile': user_profile})


def signin(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('category_management')
    else:
        form = AuthenticationForm()
    return render(request, 'signin.html', {'form': form})



def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            user_profile.date_of_birth = form.cleaned_data.get('date_of_birth')
            user_profile.location = form.cleaned_data.get('location')
            user_profile.save()
            login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})


def statistics(request):
    return render(request, 'statistics.html')


@login_required
def tags(request):
    return render(request, 'tags.html')


@login_required
def view_notes(request):
    # Chargement des catégories avec fallback MongoDB
    categories = []
    try:
        # Essayer d'abord avec l'ORM Django
        categories = list(Category.objects.filter(users=request.user))
        
        # Si pas de catégories trouvées avec l'ORM, essayer MongoDB
        if not categories:
            from pymongo import MongoClient
            from django.conf import settings
            
            mongo_uri = settings.DATABASES['default']['CLIENT']['host']
            client = MongoClient(mongo_uri)
            db = client['journalDB']
            collection = db['journal_category']
            
            # Chercher les catégories de l'utilisateur
            user_categories_data = list(collection.find({
                '$or': [
                    {'user_id': request.user.id}, 
                    {'users': request.user.id}
                ]
            }))
            client.close()
            
            # Convertir en objets compatibles avec le template
            for cat_data in user_categories_data:
                class CategoryProxy:
                    def __init__(self, data):
                        self.id = data.get('id') or data.get('_id')
                        self.name = data.get('name', '')
                        self.icon = data.get('icon', '📁')
                
                categories.append(CategoryProxy(cat_data))
                
    except Exception as e:
        print(f"Erreur chargement catégories: {e}")
        categories = []
    
    notes = Note.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'categories': categories,
        'notes': notes,
        'category': None,  # Pas de catégorie filtrée pour cette vue
    }
    return render(request, 'view_notes.html', context)


@login_required
def notes_by_category(request, category_id):
    # Essayer d'abord de récupérer la catégorie via l'ORM Django
    category = None
    categories = []
    notes = []
    
    try:
        # Essayer ORM d'abord
        category = get_object_or_404(Category, id=category_id, users=request.user)
        notes = Note.objects.filter(user=request.user, category=category).order_by('-created_at')
        categories = list(Category.objects.filter(users=request.user))
    except Exception:
        # Fallback vers MongoDB
        try:
            from pymongo import MongoClient
            from django.conf import settings
            from bson import ObjectId
            
            mongo_uri = settings.DATABASES['default']['CLIENT']['host']
            client = MongoClient(mongo_uri)
            db = client['journalDB']
            collection = db['journal_category']

            # Chercher la catégorie spécifique
            cat_doc = None
            try:
                # Essayer avec l'ID numérique
                cid_int = int(category_id)
                cat_doc = collection.find_one({
                    'id': cid_int,
                    '$or': [
                        {'user_id': request.user.id}, 
                        {'users': request.user.id}
                    ]
                })
            except (ValueError, TypeError):
                pass

            if not cat_doc:
                # Essayer avec ObjectId
                try:
                    cat_doc = collection.find_one({
                        '_id': ObjectId(str(category_id)),
                        '$or': [
                            {'user_id': request.user.id}, 
                            {'users': request.user.id}
                        ]
                    })
                except Exception:
                    pass

            # Créer un proxy pour la catégorie trouvée
            if cat_doc:
                class CategoryProxy:
                    def __init__(self, data):
                        self.id = data.get('id') or data.get('_id')
                        self.name = data.get('name', 'Catégorie sans nom')
                        self.icon = data.get('icon', '📁')
                
                category = CategoryProxy(cat_doc)
                
                # Récupérer les notes pour cette catégorie
                try:
                    category_filter_id = cat_doc.get('id') or cat_doc.get('_id')
                    notes = Note.objects.filter(
                        user=request.user, 
                        category_id=int(category_filter_id)
                    ).order_by('-created_at')
                except Exception:
                    notes = Note.objects.filter(user=request.user).order_by('-created_at')
            else:
                # Catégorie non trouvée
                class CategoryProxy:
                    def __init__(self, cid, name='Catégorie non trouvée'):
                        self.id = cid
                        self.name = name
                        self.icon = '❓'
                
                category = CategoryProxy(category_id)
                notes = []

            # Charger toutes les catégories pour la sidebar
            user_cats = list(collection.find({
                '$or': [
                    {'user_id': request.user.id}, 
                    {'users': request.user.id}
                ]
            }))
            
            for cat_data in user_cats:
                class CategoryProxy:
                    def __init__(self, data):
                        self.id = data.get('id') or data.get('_id')
                        self.name = data.get('name', '')
                        self.icon = data.get('icon', '📁')
                
                categories.append(CategoryProxy(cat_data))
            
            client.close()
            
        except Exception as e:
            print(f"Erreur lors de la récupération de la catégorie: {e}")
            # Fallback final
            class CategoryProxy:
                def __init__(self, cid):
                    self.id = cid
                    self.name = 'Erreur de chargement'
                    self.icon = '⚠️'
            
            category = CategoryProxy(category_id)
            notes = Note.objects.filter(user=request.user).order_by('-created_at')
            categories = []

    context = {
        'category': category,
        'notes': notes,
        'categories': categories,
    }
    return render(request, 'view_notes.html', context)

@login_required
def tag_create(request):
    return render(request, 'tags.html')


@login_required
def event_create(request):
    return render(request, 'create_note.html')


@csrf_exempt
@require_http_methods(["POST"])
def predict_emotion_api(request):
    """API endpoint to predict emotion from text"""
    try:
        import json
        from .utils import predict_emotion as predict_func, lr_model
        
        # Get text from POST request
        data = json.loads(request.body)
        text = data.get('text', '')
        
        if not text:
            return JsonResponse({'error': 'No text provided'}, status=400)
        
        # Predict emotion
        emotion, confidence = predict_func(text, lr_model)
        
        if emotion is None:
            return JsonResponse({'error': 'Model not available'}, status=500)
        
        return JsonResponse({
            'emotion': emotion,
            'confidence': float(confidence),
            'text': text
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def generate_recommendations(request, note_id):
    """Génère des recommandations d'activités pour une note spécifique"""
    note = get_object_or_404(Note, id=note_id, user=request.user)
    
    # Vérifier si des recommandations existent déjà
    existing_recommendation = ActivityRecommendation.objects.filter(note=note).first()
    
    if existing_recommendation:
        # Utiliser les recommandations existantes
        recommendations_data = {
            'emotion': existing_recommendation.emotion,
            'confidence': existing_recommendation.confidence,
            'activities': existing_recommendation.recommendations,
            'encouragement': existing_recommendation.encouragement,
            'color': existing_recommendation.color,
            'icon': existing_recommendation.icon,
            'emotion_display': note.get_emotion_display()
        }
        
        # Générer l'enrichissement uniquement s'il n'est pas déjà stocké en base
        if not existing_recommendation.enriched_content:
            try:
                enriched_content = perplexity_service.enrich_recommendations(
                    recommendations=existing_recommendation.recommendations,
                    emotion=existing_recommendation.emotion,
                    note_content=note.content[:500]
                )
                
                existing_recommendation.enriched_content = enriched_content
                existing_recommendation.has_enrichment = True
                existing_recommendation.enrichment_generated_at = timezone.now()
                existing_recommendation.save()
                
            except Exception as e:
                print(f"Erreur lors de l'enrichissement Perplexity: {str(e)}")
        
        # Ajouter le contenu enrichi aux données
        recommendations_data['enriched_content'] = existing_recommendation.enriched_content
    else:
        # Générer de nouvelles recommandations
        if not note.emotion:
            # Si pas d'émotion détectée, utiliser l'émotion par défaut
            emotion = 'joy'
            confidence = 0.5
        else:
            emotion = note.emotion
            confidence = note.emotion_confidence / 100 if note.emotion_confidence else 0.5
        
        # Déterminer le contexte temporel
        current_hour = datetime.now().hour
        if 6 <= current_hour < 12:
            time_context = 'morning'
        elif 12 <= current_hour < 18:
            time_context = 'afternoon'
        else:
            time_context = 'evening'
        
        context = {'time_of_day': time_context}
        
        # Générer les recommandations
        recommendations_data = recommendation_engine.get_recommendations(
            emotion=emotion,
            confidence=confidence,
            context=context
        )
        
        # Sauvegarder les recommandations en base
        recommendation_obj = ActivityRecommendation.objects.create(
            note=note,
            emotion=emotion,
            confidence=confidence,
            recommendations=recommendations_data['activities'],
            encouragement=recommendations_data['encouragement'],
            color=recommendations_data['color'],
            icon=recommendations_data['icon']
        )
        
        # Générer l'enrichissement Perplexity en arrière-plan
        try:
            enriched_content = perplexity_service.enrich_recommendations(
                recommendations=recommendations_data['activities'],
                emotion=emotion,
                note_content=note.content[:500]  # Limiter le contenu pour l'API
            )
            
            # Mettre à jour avec le contenu enrichi
            recommendation_obj.enriched_content = enriched_content
            recommendation_obj.has_enrichment = True
            recommendation_obj.enrichment_generated_at = timezone.now()
            recommendation_obj.save()
            
        except Exception as e:
             print(f"Erreur lors de l'enrichissement Perplexity: {str(e)}")
             # Continuer sans enrichissement en cas d'erreur
        
        # Ajouter le contenu enrichi aux données de recommandation
        recommendations_data['enriched_content'] = recommendation_obj.enriched_content
    
    # Construire la séparation principales vs autres recommandations
    primary_activities = recommendations_data.get('activities', [])
    emotion_key = recommendations_data.get('emotion')
    all_activities = []
    try:
        all_activities = recommendation_engine.recommendations_db.get(emotion_key, {}).get('activities', [])
    except Exception:
        all_activities = []
    other_activities = [a for a in all_activities if a not in primary_activities]

    context = {
        'note': note,
        'recommendations': recommendations_data,
        'primary_activities': primary_activities,
        'other_activities': other_activities,
    }
    
    return render(request, 'recommendations.html', context)


@login_required 
def regenerate_recommendations(request, note_id):
    """Régénère de nouvelles recommandations pour une note"""
    note = get_object_or_404(Note, id=note_id, user=request.user)
    
    # Supprimer les anciennes recommandations
    ActivityRecommendation.objects.filter(note=note).delete()
    
    # Rediriger vers la génération de nouvelles recommandations
    return redirect('generate_recommendations', note_id=note_id)


@login_required
def media_upload(request):
    """Vue pour uploader des médias (images/vidéos)"""
    
    if request.method == 'POST':
        upload_type = request.POST.get('upload_type', 'single')
        
        if upload_type == 'single':
            # VALIDATION MANUELLE (contourne le bug Djongo avec ForeignKey)
            file = request.FILES.get('file')
            category_id = request.POST.get('category')
            
            # Validation du fichier
            if not file:
                messages.error(request, '❌ Vous devez sélectionner un fichier à uploader.')
                user_categories = Category.objects.filter(users=request.user)
                context = {
                    'single_form': MediaUploadForm(),
                    'multiple_form': MultipleMediaUploadForm(user=request.user),
                    'categories': user_categories,
                }
                return render(request, 'media_upload.html', context)
            
            # Validation de la catégorie
            if not category_id:
                messages.error(request, '❌ Vous devez sélectionner une catégorie.')
                user_categories = Category.objects.filter(users=request.user)
                context = {
                    'single_form': MediaUploadForm(),
                    'multiple_form': MultipleMediaUploadForm(user=request.user),
                    'categories': user_categories,
                }
                return render(request, 'media_upload.html', context)
            
            # Utiliser la méthode clean_file de MediaUploadForm pour valider le fichier
            upload_form = MediaUploadForm()
            upload_form.cleaned_data = {'file': file}
            
            try:
                validated_file = upload_form.clean_file()
            except forms.ValidationError as e:
                messages.error(request, str(e.message))
                user_categories = Category.objects.filter(users=request.user)
                context = {
                    'single_form': MediaUploadForm(),
                    'multiple_form': MultipleMediaUploadForm(user=request.user),
                    'categories': user_categories,
                }
                return render(request, 'media_upload.html', context)
            
            # Si tout est valide, créer le média
            try:
                media = Media(
                    user=request.user,
                    file=validated_file,
                    title=request.POST.get('title', ''),
                    description=request.POST.get('description', ''),
                    album=request.POST.get('album', ''),
                )
                
                # Ajouter la catégorie
                try:
                    media.category_id = int(category_id)
                except (ValueError, TypeError):
                    pass
                
                # Extraire dimensions pour images
                ext = validated_file.name.split('.')[-1].lower()
                if ext in ['jpg', 'jpeg', 'png']:
                    try:
                        img = Image.open(validated_file)
                        media.width, media.height = img.size
                    except Exception as e:
                        print(f"Erreur extraction dimensions: {e}")
                
                media.save()
                messages.success(request, f'✅ Média "{media.title or validated_file.name}" uploadé avec succès!')
                
                return redirect('gallery')
            except Exception as e:
                messages.error(request, f'❌ Erreur lors de l\'upload: {str(e)}')
        
        else:  # multiple
            # VALIDATION MANUELLE pour upload multiple (contourne bug Djongo)
            files = request.FILES.getlist('files')
            album = request.POST.get('album', '')
            auto_analyze = request.POST.get('auto_analyze') == 'on'
            
            # Validation des fichiers
            if not files:
                messages.error(request, '❌ Vous devez sélectionner au moins un fichier.')
                user_categories = Category.objects.filter(users=request.user)
                context = {
                    'single_form': MediaUploadForm(),
                    'multiple_form': MultipleMediaUploadForm(user=request.user),
                    'categories': user_categories,
                }
                return render(request, 'media_upload.html', context)
            
            # Validation du nombre de fichiers
            if len(files) > 3:
                messages.error(request, 
                    f'❌ Trop de fichiers sélectionnés!\n\n'
                    f'📋 Maximum autorisé: 3 images\n'
                    f'Nombre sélectionné: {len(files)}'
                )
                user_categories = Category.objects.filter(users=request.user)
                context = {
                    'single_form': MediaUploadForm(),
                    'multiple_form': MultipleMediaUploadForm(user=request.user),
                    'categories': user_categories,
                }
                return render(request, 'media_upload.html', context)
            
            # Valider chaque fichier ET sa catégorie
            upload_form = MediaUploadForm()
            files_data = []
            
            for index, file in enumerate(files):
                # Récupérer la catégorie pour ce fichier spécifique
                category_id = request.POST.get(f'category_{index}')
                
                # Validation de la catégorie pour ce fichier
                if not category_id:
                    messages.error(request, f'❌ Vous devez sélectionner une catégorie pour l\'image "{file.name}".')
                    user_categories = Category.objects.filter(users=request.user)
                    context = {
                        'single_form': MediaUploadForm(),
                        'multiple_form': MultipleMediaUploadForm(user=request.user),
                        'categories': user_categories,
                    }
                    return render(request, 'media_upload.html', context)
                
                # Validation du fichier
                upload_form.cleaned_data = {'file': file}
                try:
                    validated_file = upload_form.clean_file()
                    files_data.append({
                        'file': validated_file,
                        'category_id': category_id,
                        'title': request.POST.get(f'title_{index}', ''),
                        'description': request.POST.get(f'description_{index}', ''),
                        'album': request.POST.get(f'album_{index}', album),  # Album individuel ou global
                        'auto_analyze': request.POST.get(f'auto_analyze_{index}') == 'on'
                    })
                except forms.ValidationError as e:
                    messages.error(request, str(e.message))
                    user_categories = Category.objects.filter(users=request.user)
                    context = {
                        'single_form': MediaUploadForm(),
                        'multiple_form': MultipleMediaUploadForm(user=request.user),
                        'categories': user_categories,
                    }
                    return render(request, 'media_upload.html', context)
            
            # Si tout est valide, uploader les fichiers
            uploaded_count = 0
            for file_data in files_data:
                try:
                    media = Media(
                        user=request.user,
                        file=file_data['file'],
                        title=file_data['title'],
                        description=file_data['description'],
                        album=file_data['album']
                    )
                    
                    # Ajouter la catégorie
                    try:
                        media.category_id = int(file_data['category_id'])
                    except (ValueError, TypeError):
                        pass
                    
                    # Extraire dimensions pour images
                    ext = file_data['file'].name.split('.')[-1].lower()
                    if ext in ['jpg', 'jpeg', 'png']:
                        try:
                            img = Image.open(file_data['file'])
                            media.width, media.height = img.size
                        except Exception as e:
                            print(f"Erreur extraction dimensions: {e}")
                    
                    media.save()
                    uploaded_count += 1
                    
                    # Lancer analyse IA si auto_analyze est True
                    if file_data['auto_analyze'] and media.media_type == 'image':
                        print(f"🤖 Lancement analyse IA pour {media.file.name}")
                        thread = threading.Thread(target=analyze_media_async, args=(media.id,))
                        thread.daemon = True
                        thread.start()
                    
                except Exception as e:
                    messages.error(request, f'❌ Erreur upload {file.name}: {str(e)}')
            
            if uploaded_count > 0:
                messages.success(request, f'✅ {uploaded_count} média(s) uploadé(s) avec succès!')
            return redirect('gallery')
    
    else:
        single_form = MediaUploadForm()
        multiple_form = MultipleMediaUploadForm(user=request.user)
    
    # Récupérer les catégories de l'utilisateur connecté avec PyMongo
    from pymongo import MongoClient
    from django.conf import settings
    
    mongo_uri = settings.DATABASES['default']['CLIENT']['host']
    client = MongoClient(mongo_uri)
    db = client['journalDB']
    collection = db['journal_category']
    
    # Charger les catégories depuis MongoDB (recherche par 'user_id' scalar ou présence de l'utilisateur dans le tableau 'users')
    user_categories_data = list(collection.find({'$or': [{'user_id': request.user.id}, {'users': request.user.id}]}))
    client.close()
    
    # Convertir en objets simples pour le template
    user_categories = []
    for cat_data in user_categories_data:
        class CategoryProxy:
            def __init__(self, data):
                self.id = data.get('id')
                self.name = data.get('name', '')
                self.icon = data.get('icon', '')
                users = data.get('users')
                # store primary user id for backward compatibility
                try:
                    self.user_id = users[0] if isinstance(users, list) and users else users
                except Exception:
                    self.user_id = users
        
        user_categories.append(CategoryProxy(cat_data))
    
    context = {
        'single_form': MediaUploadForm(),
        'multiple_form': MultipleMediaUploadForm(user=request.user),
        'categories': user_categories,
    }
    
    return render(request, 'media_upload.html', context)



@login_required
def media_detail(request, media_id):
    """Vue détaillée d'un média avec analyse IA"""
    
    media = get_object_or_404(Media, id=media_id, user=request.user)
    
    # Récupérer l'analyse IA (avec gestion robuste des bugs Djongo)
    analysis = None
    try:
        # Essayer d'abord avec filter().first() (plus stable avec Djongo)
        analyses = list(MediaAnalysis.objects.filter(media=media))
        if analyses:
            analysis = analyses[0]  # Prendre la première analyse
        else:
            # Créer une analyse vide si aucune n'existe
            analysis = MediaAnalysis.objects.create(media=media)
    except Exception as e:
        print(f"Erreur récupération analyse (Djongo): {e}")
        # En cas d'erreur Djongo, créer une analyse temporaire
        analysis = MediaAnalysis(media=media)
        analysis.detected_objects = []
        analysis.dominant_colors = []
        analysis.detected_emotions = []
        analysis.detected_locations = []
        analysis.ai_title = ""
        analysis.ai_description = ""
    
    # Récupérer les tags
    tags = MediaTag.objects.filter(media=media)
    
    # Traiter l'ajout de tag manuel
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_tag':
            tag_form = MediaTagForm(request.POST)
            if tag_form.is_valid():
                tag = tag_form.save(commit=False)
                tag.media = media
                tag.source = 'manual'
                try:
                    tag.save()
                    messages.success(request, f'✅ Tag "{tag.name}" ajouté!')
                except Exception as e:
                    messages.error(request, f'❌ Ce tag existe déjà.')
                return redirect('media_detail', media_id=media.id)
        
        elif action == 'toggle_favorite':
            media.is_favorite = not media.is_favorite
            media.save()
            return JsonResponse({'success': True, 'is_favorite': media.is_favorite})
        
        elif action == 'analyze':
            # TODO: Lancer l'analyse IA
            messages.info(request, '🤖 Analyse IA en cours...')
            return redirect('media_detail', media_id=media.id)
    
    # Médias similaires (même catégorie)
    similar_media = Media.objects.filter(
        user=request.user,
        category=media.category
    ).exclude(id=media.id)[:6]
    
    context = {
        'media': media,
        'analysis': analysis,
        'tags': tags,
        'tag_form': MediaTagForm(),
        'similar_media': similar_media,
    }
    
    return render(request, 'media_detail.html', context)



@login_required
def media_edit(request, media_id):
    """Vue pour éditer un média"""
    
    media = get_object_or_404(Media, id=media_id, user=request.user)
    # Prepare user categories once (ORM preferred, fallback to Mongo)
    try:
        user_categories = list(Category.objects.filter(users=request.user))
    except Exception:
        user_categories = []

    if not user_categories:
        try:
            from pymongo import MongoClient
            from django.conf import settings
            mongo_uri = settings.DATABASES['default']['CLIENT']['host']
            client = MongoClient(mongo_uri)
            db = client['journalDB']
            collection = db['journal_category']
            user_cats = list(collection.find({'$or': [{'user_id': request.user.id}, {'users': request.user.id}]}))
            client.close()

            user_categories = []
            for cat_data in user_cats:
                class CategoryProxy:
                    def __init__(self, data):
                        self.id = data.get('id') or data.get('_id')
                        self.name = data.get('name', '')
                        self.icon = data.get('icon', '')
                user_categories.append(CategoryProxy(cat_data))
        except Exception:
            user_categories = []
    
    if request.method == 'POST':
        # Validation manuelle pour éviter les bugs Djongo avec ForeignKey validation
        new_file = request.FILES.get('file')
        
        # Si un nouveau fichier est fourni, le valider
        if new_file:
            edit_form = MediaEditForm()
            edit_form.cleaned_data = {'file': new_file}
            
            try:
                validated_file = edit_form.clean_file()
                
                # Supprimer l'ancien fichier
                if media.file:
                    try:
                        import os
                        old_file_path = media.file.path
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    except Exception as e:
                        print(f"Erreur suppression ancien fichier: {e}")
                
                # Remplacer par le nouveau fichier
                media.file = validated_file
                
                # Extraire les nouvelles dimensions
                ext = validated_file.name.split('.')[-1].lower()
                if ext in ['jpg', 'jpeg', 'png']:
                    try:
                        img = Image.open(validated_file)
                        media.width, media.height = img.size
                    except Exception as e:
                        print(f"Erreur extraction dimensions: {e}")
                
            except forms.ValidationError as e:
                messages.error(request, str(e.message))
                context = {
                    'form': MediaEditForm(instance=media),
                    'media': media,
                    'categories': user_categories,
                }
                return render(request, 'media_edit.html', context)
        
        # Mise à jour des autres champs
        try:
            media.title = request.POST.get('title', '')
            media.description = request.POST.get('description', '')
            media.album = request.POST.get('album', '')
            media.is_favorite = 'is_favorite' in request.POST
            
            # Gérer la catégorie
            category_id = request.POST.get('category')
            if category_id:
                try:
                    media.category_id = int(category_id)
                except (ValueError, TypeError):
                    media.category = None
            else:
                media.category = None
            
            media.save()
            
            if new_file:
                messages.success(request, '✅ Média et image mis à jour avec succès!')
            else:
                messages.success(request, '✅ Média mis à jour avec succès!')
            
            return redirect('media_detail', media_id=media.id)
        except Exception as e:
            messages.error(request, f'❌ Erreur lors de la mise à jour: {str(e)}')
    
    # Créer un formulaire pour l'affichage
    form = MediaEditForm(instance=media)
    
    context = {
        'form': form,
        'media': media,
        'categories': user_categories,
    }
    
    return render(request, 'media_edit.html', context)


@login_required
def media_delete(request, media_id):
    """Vue pour supprimer un média"""
    
    try:
        media = get_object_or_404(Media, id=media_id, user=request.user)
    except Exception as e:
        messages.error(request, f'❌ Média introuvable (ID: {media_id}). Il a peut-être déjà été supprimé.')
        return redirect('gallery')
    
    if request.method == 'POST':
        try:
            # Supprimer le fichier physique
            if media.file:
                if os.path.isfile(media.file.path):
                    os.remove(media.file.path)
            
            if media.thumbnail:
                if os.path.isfile(media.thumbnail.path):
                    os.remove(media.thumbnail.path)
            
            media_title = media.title or media.file.name
            media.delete()
            
            messages.success(request, f'✅ "{media_title}" supprimé avec succès!')
            return redirect('gallery')
        except Exception as e:
            messages.error(request, f'❌ Erreur lors de la suppression: {str(e)}')
            return redirect('gallery')
    
    context = {
        'media': media,
    }
    
    return render(request, 'media_delete_confirm.html', context)


@login_required
def media_delete_tag(request, media_id, tag_id):
    """Supprimer un tag d'un média"""
    
    media = get_object_or_404(Media, id=media_id, user=request.user)
    tag = get_object_or_404(MediaTag, id=tag_id, media=media)
    
    tag_name = tag.name
    tag.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': f'Tag "{tag_name}" supprimé'})
    
    messages.success(request, f'✅ Tag "{tag_name}" supprimé!')
    return redirect('media_detail', media_id=media.id)


def analyze_media_async(media_id):
    """Fonction pour analyser un média en arrière-plan"""
    try:
        # Gérer les différents types d'ID (ObjectId MongoDB ou entier Django)
        media = Media.objects.get(id=media_id)
        
        # Vérifier que c'est une image
        if media.media_type != 'image':
            print(f"⚠️ Analyse IA non supportée pour {media.media_type}")
            return
        
        print(f"🔍 Démarrage analyse IA pour {media.file.name}")
        
        # Lancer l'analyse Vision AI
        results = analyze_media_vision(media.file.path)
        
        # SOLUTION DJONGO : Supprimer toutes les anciennes analyses pour éviter les doublons
        try:
            MediaAnalysis.objects.filter(media=media).delete()
        except Exception as e:
            print(f"⚠️ Nettoyage analyses (ignoré): {e}")
        
        # Créer une NOUVELLE analyse
        analysis = MediaAnalysis(media=media)
        
        # Mettre à jour avec les résultats
        analysis.detected_objects = [obj['object'] for obj in results.get('detected_objects', [])]
        analysis.detected_locations = [f"{loc['landmark']}, {loc['city']}" for loc in results.get('detected_locations', [])]
        analysis.dominant_colors = [color['hex'] for color in results.get('dominant_colors', [])]
        analysis.detected_emotions = [emo['emotion'] for emo in results.get('detected_emotions', [])]
        analysis.ai_description = results.get('image_description', '')
        
        # Générer un titre basé sur les objets détectés
        objects = results.get('detected_objects', [])
        if objects:
            top_objects = [obj['object'] for obj in objects[:3]]
            analysis.ai_title = f"Photo avec {', '.join(top_objects)}"
        else:
            analysis.ai_title = "Photo analysée par IA"
        
        # Calculer score de confiance moyen
        confidences = [obj.get('confidence', 0) for obj in results.get('detected_objects', [])]
        analysis.confidence_score = sum(confidences) / len(confidences) if confidences else 0.5
        
        # IMPORTANT : Sauvegarder AVANT de marquer le média comme analysé
        analysis.save()
        print(f"💾 Analyse sauvegardée : {analysis.ai_title}")
        
        # Marquer le média comme analysé
        media.is_analyzed = True
        media.save()
        
        # Supprimer les anciens tags IA pour éviter les doublons
        try:
            MediaTag.objects.filter(media=media, source='ai').delete()
        except Exception as e:
            print(f"⚠️ Nettoyage tags (ignoré): {e}")
        
        # Créer des tags automatiques
        for obj_data in results.get('detected_objects', [])[:5]:  # Top 5 objets
            try:
                tag, created = MediaTag.objects.get_or_create(
                    media=media,
                    name=obj_data['object'],
                    defaults={
                        'source': 'ai',
                        'confidence': int(obj_data.get('confidence', 0) * 100)
                    }
                )
                if created:
                    print(f"🏷️  Tag créé: {tag.name}")
            except Exception as e:
                print(f"⚠️ Erreur création tag '{obj_data['object']}': {e}")
        
        print(f"✅ Analyse IA terminée pour {media.file.name}")
        
    except Exception as e:
        print(f"❌ Erreur analyse IA: {e}")
        import traceback
        traceback.print_exc()


@login_required
def media_analyze(request, media_id):
    """Lancer l'analyse IA d'un média (AJAX)"""
    
    media = get_object_or_404(Media, id=media_id, user=request.user)
    
    if request.method == 'POST':
        try:
            # Vérifier que c'est une image
            if media.media_type != 'image':
                return JsonResponse({
                    'success': False,
                    'error': '⚠️ L\'analyse IA n\'est disponible que pour les images pour le moment'
                })
            
            # Créer ou récupérer l'objet d'analyse
            analysis = MediaAnalysis.objects.filter(media=media).first()
            if not analysis:
                analysis = MediaAnalysis.objects.create(media=media)
            
            # Marquer comme en cours d'analyse
            analysis.ai_title = "🔄 Analyse en cours..."
            analysis.ai_description = "L'intelligence artificielle analyse votre image..."
            analysis.save()
            
            # Lancer l'analyse en arrière-plan
            thread = threading.Thread(target=analyze_media_async, args=(media_id,))
            thread.daemon = True
            thread.start()
            
            return JsonResponse({
                'success': True,
                'message': '🤖 Analyse IA démarrée ! Actualisez la page dans quelques secondes pour voir les résultats.',
                'analysis_id': str(analysis.id) if analysis.id else None  # Convertir ObjectId en string seulement pour JSON
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'❌ Erreur: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'}, status=405)



@login_required
def smart_albums(request):
    """Vue pour gérer les albums intelligents"""
    
    albums = SmartAlbum.objects.filter(user=request.user)
    
    context = {
        'albums': albums,
    }
    
    return render(request, 'smart_albums.html', context)

