from django.shortcuts import render, redirect, get_object_or_404
import re
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
import logging
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .forms import CustomUserCreationForm, NoteForm
from .forms import GoalForm
from .models import UserProfile, Category, Note, Goal
from .utils import lr_model, clean_text, predict_emotion, predict_goal_duration, generate_motivation_message
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect


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
    return render(request, 'dashboard.html')

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
def goals_list(request):
    # Use direct MongoDB access to avoid JSON parsing issues with djongo
    from pymongo import MongoClient
    from django.conf import settings
    
    client = MongoClient(settings.DATABASES['default']['CLIENT']['host'])
    db = client[settings.DATABASES['default']['NAME']]
    collection = db['journal_goal']
    
    # Get all goals for current user
    goals_data = list(collection.find({'user_id': request.user.id}).sort('created_at', -1))
    
    # Convert to Goal objects
    goals = []
    for goal_data in goals_data:
        # Parse milestones if it's a JSON string
        milestones = goal_data.get('milestones', [])
        if isinstance(milestones, str):
            import json
            try:
                milestones = json.loads(milestones)
            except:
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
        
        # Add AI motivation to each goal
        try:
            goal.ai_motivation = generate_motivation_message(goal, request.user)
            print(f"DEBUG: AI motivation generated for {goal.title}: {goal.ai_motivation['message'][:50]}")
        except Exception as e:
            print(f"DEBUG ERROR: Failed to generate AI motivation for {goal.title}: {e}")
            import traceback
            traceback.print_exc()
            goal.ai_motivation = None
        
        goals.append(goal)
    
    return render(request, 'goals/list.html', {'goals': goals})


@login_required
def goal_detail(request, slug):
    # Use direct MongoDB access to avoid JSON parsing issues with djongo
    from pymongo import MongoClient
    from django.conf import settings
    
    client = MongoClient(settings.DATABASES['default']['CLIENT']['host'])
    db = client[settings.DATABASES['default']['NAME']]
    collection = db['journal_goal']
    
    # Find goal by slug and user_id
    goal_data = collection.find_one({'slug': slug, 'user_id': request.user.id})
    if not goal_data:
        raise Http404("Objectif non trouvé")
    
    # Parse milestones if it's a JSON string
    milestones = goal_data.get('milestones', [])
    if isinstance(milestones, str):
        import json
        try:
            milestones = json.loads(milestones)
        except:
            milestones = []
    if not isinstance(milestones, list):
        milestones = []
    
    # Create a Goal instance manually with the data
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
    
    # Generate AI predictions
    duration_min, duration_max, complexity = predict_goal_duration(goal)
    motivation_data = generate_motivation_message(goal, request.user)
    
    context = {
        'goal': goal,
        'duration_min': duration_min,
        'duration_max': duration_max,
        'complexity': complexity,
        'motivation': motivation_data
    }
    
    return render(request, 'goals/detail.html', context)


@login_required
def goal_create(request):
    if request.method == 'POST':
        form = GoalForm(request.POST, user=request.user)
        # log raw posted milestones for debugging
        try:
            logging.getLogger(__name__).info('Posted milestones raw: %s', request.POST.get('milestones'))
        except Exception:
            pass
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            form.save_m2m()
            return redirect('goals_list')
        else:
            # log errors for debugging
            logging.getLogger(__name__).warning('Goal create form invalid: %s', form.errors.as_json())
    else:
        form = GoalForm(user=request.user)
    return render(request, 'goals/form.html', {'form': form, 'creating': True})


@login_required
def goal_update(request, slug):
    # Use direct MongoDB access to avoid JSON parsing issues
    from pymongo import MongoClient
    from django.conf import settings
    
    client = MongoClient(settings.DATABASES['default']['CLIENT']['host'])
    db = client[settings.DATABASES['default']['NAME']]
    collection = db['journal_goal']
    
    # Find goal by slug and user_id
    goal_data = collection.find_one({'slug': slug, 'user_id': request.user.id})
    if not goal_data:
        raise Http404("Objectif non trouvé")
    
    # Parse milestones if stored as JSON string
    milestones = goal_data.get('milestones', [])
    if isinstance(milestones, str):
        try:
            import json
            milestones = json.loads(milestones)
        except:
            milestones = []
    if not isinstance(milestones, list):
        milestones = []
    
    # Create a Goal instance for the form
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
            # Calculate progress from milestones
            milestones = form.cleaned_data.get('milestones', [])
            if isinstance(milestones, list) and len(milestones) > 0:
                total = len(milestones)
                done_count = sum(1 for m in milestones if isinstance(m, dict) and m.get('done'))
                progress = int((done_count / total) * 100)
            else:
                progress = 0
            
            # Find by slug and user_id and update
            result = collection.update_one(
                {'slug': slug, 'user_id': request.user.id},
                {'$set': {
                    'title': form.cleaned_data['title'],
                    'description': form.cleaned_data.get('description', ''),
                    'status': form.cleaned_data['status'],
                    'start_date': form.cleaned_data.get('start_date'),
                    'end_date': form.cleaned_data.get('end_date'),
                    'priority': form.cleaned_data.get('priority', Goal.PRIORITY_MEDIUM),
                    'difficulty': form.cleaned_data.get('difficulty', 3),
                    'reward': form.cleaned_data.get('reward', ''),
                    'recurrence': form.cleaned_data.get('recurrence', ''),
                    'motivation_level': form.cleaned_data.get('motivation_level', 5),
                    'milestones': milestones,
                    'category_id': form.cleaned_data.get('category').id if form.cleaned_data.get('category') else None,
                    'progress_cached': progress
                }}
            )
            
            if result.modified_count > 0:
                return redirect('goal_detail', slug=slug)
            else:
                logging.getLogger(__name__).warning('No document updated for slug: %s', slug)
        else:
            logging.getLogger(__name__).warning('Goal update form invalid: %s', form.errors.as_json())
    else:
        form = GoalForm(instance=goal, user=request.user)
    return render(request, 'goals/form.html', {'form': form, 'creating': False, 'goal': goal})


@login_required
def goal_delete(request, slug):
    # Use direct MongoDB access to avoid JSON parsing issues
    from pymongo import MongoClient
    from django.conf import settings
    
    client = MongoClient(settings.DATABASES['default']['CLIENT']['host'])
    db = client[settings.DATABASES['default']['NAME']]
    collection = db['journal_goal']
    
    # Find goal by slug and user_id
    goal_data = collection.find_one({'slug': slug, 'user_id': request.user.id})
    if not goal_data:
        raise Http404("Objectif non trouvé")
    
    # Create a Goal instance for the template
    goal = Goal(
        id=goal_data.get('_id'),
        user=request.user,
        title=goal_data.get('title', ''),
        description=goal_data.get('description', ''),
        slug=goal_data.get('slug', ''),
    )
    
    if request.method == 'POST':
        # Delete by slug and user_id
        result = collection.delete_one({'slug': slug, 'user_id': request.user.id})
        
        if result.deleted_count > 0:
            return redirect('goals_list')
        else:
            logging.getLogger(__name__).warning('No document deleted for slug: %s', slug)
    return render(request, 'goals/confirm_delete.html', {'goal': goal})


@csrf_protect
@login_required
@require_POST
def toggle_milestone(request, slug):
    """Toggle milestone done state. Expects JSON body: {"index": 0}. Returns {"ok": True, "done": True, "progress": 42} or error.
    This view now requires POST and an authenticated user. It always returns JsonResponse on handled errors so the frontend can parse responses safely.
    """
    import json
    from pymongo import MongoClient
    from django.conf import settings
    
    # Use direct MongoDB access to avoid JSON parsing issues
    client = MongoClient(settings.DATABASES['default']['CLIENT']['host'])
    db = client[settings.DATABASES['default']['NAME']]
    collection = db['journal_goal']
    
    # Find goal by slug and user_id
    goal_data = collection.find_one({'slug': slug, 'user_id': request.user.id})
    if not goal_data:
        return JsonResponse({'ok': False, 'error': 'Objectif non trouvé'}, status=404)
    
    try:
        data = json.loads(request.body.decode('utf-8'))
        idx = int(data.get('index', -1))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Invalid payload'}, status=400)

    # Parse milestones if stored as JSON string
    milestones = goal_data.get('milestones', [])
    if isinstance(milestones, str):
        try:
            milestones = json.loads(milestones)
        except:
            milestones = []
    if not isinstance(milestones, list):
        milestones = []
    
    if idx < 0 or idx >= len(milestones):
        return JsonResponse({'ok': False, 'error': 'Invalid index'}, status=400)

    # toggle
    current = bool(milestones[idx].get('done'))
    new_done = not current

    # recalculate cached progress as percentage of completed milestones
    total = len(milestones)
    # Count done after this toggle
    done_count = sum(1 for i, m in enumerate(milestones) if (i == idx and new_done) or (i != idx and m.get('done')))
    progress = int((done_count / total) * 100) if total > 0 else 0
    
    # Automatically mark goal as completed when all tasks are done
    current_status = goal_data.get('status', Goal.STATUS_ONGOING)
    new_status = current_status
    if total > 0 and done_count == total:
        new_status = Goal.STATUS_COMPLETED
    # If goal was completed but not all tasks are done anymore, set it back to ongoing
    elif current_status == Goal.STATUS_COMPLETED and done_count < total:
        new_status = Goal.STATUS_ONGOING
    
    # Direct MongoDB update using pymongo
    from pymongo import MongoClient
    from django.conf import settings
    
    client = MongoClient(settings.DATABASES['default']['CLIENT']['host'])
    db = client[settings.DATABASES['default']['NAME']]
    collection = db['journal_goal']
    
    # Update milestone in-memory then write back the full milestones array to avoid
    # dotted-path write errors when the DB stores milestones as a string.
    try:
        # ensure each milestone is a dict
        for i, m in enumerate(milestones):
            if not isinstance(m, dict):
                milestones[i] = {'title': str(m), 'done': False}

        milestones[idx]['done'] = bool(new_done)

        # write the full milestones array back to the document
        result = collection.update_one(
            {'slug': slug, 'user_id': request.user.id},
            {'$set': {
                'milestones': milestones,
                'progress_cached': progress,
                'status': new_status
            }}
        )

        if result.modified_count == 0:
            logging.getLogger(__name__).warning('No document updated in toggle_milestone for slug: %s', slug)
            return JsonResponse({'ok': False, 'error': 'Update failed'}, status=500)

        return JsonResponse({
            'ok': True,
            'done': new_done,
            'progress': progress,
            'status': new_status
        })
    except Exception as e:
        logging.getLogger(__name__).exception('Error updating milestone for slug %s: %s', slug, e)
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

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