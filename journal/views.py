from django.shortcuts import render, redirect, get_object_or_404
import re
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import IntegrityError
from .forms import CustomUserCreationForm, NoteForm
from .models import UserProfile, Category, Note

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
            note.save()
            return redirect('home')
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