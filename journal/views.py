from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import CustomUserCreationForm
from .models import UserProfile, Category

def home(request):
    return render(request, 'home.html')

def base(request):
    return render(request, 'base.html')

@login_required
def category_management(request):
    if request.method == 'POST':
        category_name = request.POST.get('categoryName')
        category_icon = request.POST.get('categoryIcon')
        if category_name:
            try:
                category = Category.objects.create(user=request.user, name=category_name, icon=category_icon)
                return JsonResponse({'success': True, 'category': {'name': category.name, 'icon': category.icon}})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Category name is required.'})
    categories = Category.objects.filter(user=request.user)
    return render(request, 'category_management.html', {'categories': categories})

def create_note(request):
    return render(request, 'create_note.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def gallery(request):
    return render(request, 'gallery.html')

def hello(request):
    return render(request, 'hello.html')

def modern_notes(request):
    return render(request, 'modern_notes.html')

@login_required
def profile(request):
    user_profile = request.user.userprofile
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
                return redirect('category_management')  # Redirect to category_management after login
    else:
        form = AuthenticationForm()
    return render(request, 'signin.html', {'form': form})

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.userprofile.date_of_birth = form.cleaned_data.get('date_of_birth')
            user.userprofile.location = form.cleaned_data.get('location')
            user.userprofile.save()
            login(request, user)
            return redirect('home')  # Redirect to home or a success page
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})

def statistics(request):
    return render(request, 'statistics.html')

def tags(request):
    return render(request, 'tags.html')

def view_notes(request):
    return render(request, 'view_notes.html')

def tag_create(request):
    return render(request, 'tags.html')

def event_create(request):
    return render(request, 'create_note.html')
