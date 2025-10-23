from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
import re
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .forms import CustomUserCreationForm, NoteForm
from .models import UserProfile, Category, Note, ActivityRecommendation
from .utils import lr_model, clean_text, predict_emotion
from .recommendation_engine import recommendation_engine
from .perplexity_service import perplexity_service
from datetime import datetime
import json


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
def category_management(request):
    if request.method == 'POST':
        category_name = (request.POST.get('categoryName') or '').strip()
        category_icon = request.POST.get('categoryIcon')
        if category_name:
            try:
                # Créer ou récupérer la catégorie globale par nom
                category, created = Category.objects.get_or_create(name=category_name, defaults={'icon': category_icon})
                # Mettre à jour l'icône si fournie (facultatif)
                if category_icon:
                    category.icon = category_icon
                    category.save() 
                # Associer l'utilisateur à la catégorie
                category.users.add(request.user)
                return JsonResponse({'success': True, 'category': {'id': category.id, 'name': category.name, 'icon': category.icon}})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Category name is required.'})
    categories = Category.objects.filter(users=request.user)
    return render(request, 'category_management.html', {'categories': categories})

@login_required
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id, users=request.user)
    if request.method == 'POST':
        category_name = (request.POST.get('categoryName') or '').strip()
        category_icon = request.POST.get('categoryIcon')
        if category_name:
            try:
                # Modifier le nom et l'icône de la catégorie (impacte tous les utilisateurs liés)
                category.name = category_name
                category.icon = category_icon
                category.save()
                return JsonResponse({'success': True, 'category': {'id': category.id, 'name': category.name, 'icon': category.icon}})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Category name is required.'})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@login_required
def delete_category(request, category_id):
    if request.method == 'POST':
        category = get_object_or_404(Category, id=category_id, users=request.user)
        try:
            # Détacher l'utilisateur de la catégorie (ne pas supprimer la catégorie globale)
            category.users.remove(request.user)
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@login_required
def dashboard(request):
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
    categories = Category.objects.filter(users=request.user)
    notes = Note.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'categories': categories,
        'notes': notes,
    }
    return render(request, 'view_notes.html', context)

@login_required
def notes_by_category(request, category_id):
    category = get_object_or_404(Category, id=category_id, users=request.user)
    notes = Note.objects.filter(user=request.user, category=category).order_by('-created_at')
    categories = Category.objects.filter(users=request.user)
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
