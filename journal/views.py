from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django import forms
from .forms import (
    CustomUserCreationForm, 
    MediaUploadForm, 
    MultipleMediaUploadForm, 
    MediaEditForm, 
    GalleryFilterForm,
    MediaTagForm
)
from .models import UserProfile, Category, Media, MediaAnalysis, MediaTag, SmartAlbum
from .services.vision_service import analyze_media_vision
import json
from PIL import Image
import os
import threading

def home(request):
    return render(request, 'home.html')

@login_required
def base(request):
    return render(request, 'base.html')

@login_required
def category_management(request):
    if request.method == 'POST':
        category_name = request.POST.get('categoryName')
        category_icon = request.POST.get('categoryIcon')
        if category_name:
            # Check if a category with the same name already exists for the current user
            if Category.objects.filter(user=request.user, name=category_name).exists():
                return JsonResponse({'success': False, 'error': 'Category with this name already exists.'})
            try:
                category = Category.objects.create(user=request.user, name=category_name, icon=category_icon)
                return JsonResponse({'success': True, 'category': {'name': category.name, 'icon': category.icon}})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Category name is required.'})
    categories = Category.objects.filter(user=request.user)
    return render(request, 'category_management.html', {'categories': categories})

@login_required
def create_note(request):
    return render(request, 'create_note.html')

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@login_required
def gallery(request):
    """Vue principale de la galerie avec filtres et recherche"""
    
    try:
        # Récupérer tous les médias de l'utilisateur
        media_list = Media.objects.filter(user=request.user)
    except Exception as e:
        # Si la table n'existe pas encore, créer une liste vide
        print(f"Erreur lors de la récupération des médias: {e}")
        media_list = Media.objects.none()
    
    # Initialiser le formulaire de filtre
    filter_form = GalleryFilterForm(user=request.user, data=request.GET or None)
    
    # Appliquer les filtres
    if filter_form.is_valid():
        # Recherche textuelle
        search_query = filter_form.cleaned_data.get('search')
        if search_query:
            media_list = media_list.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(tags__name__icontains=search_query)
            ).distinct()
        
        # Filtre par type de média
        media_type = filter_form.cleaned_data.get('media_type')
        if media_type:
            media_list = media_list.filter(media_type=media_type)
        
        # Filtre par catégorie
        category = filter_form.cleaned_data.get('category')
        if category:
            media_list = media_list.filter(category=category)
        
        # Filtre favoris
        is_favorite = filter_form.cleaned_data.get('is_favorite')
        if is_favorite:
            media_list = media_list.filter(is_favorite=True)
        
        # Filtre analysés par IA
        is_analyzed = filter_form.cleaned_data.get('is_analyzed')
        if is_analyzed:
            media_list = media_list.filter(is_analyzed=True)
        
        # Tri
        sort_by = filter_form.cleaned_data.get('sort_by') or '-uploaded_at'
        media_list = media_list.order_by(sort_by)
    else:
        media_list = media_list.order_by('-uploaded_at')
    
    # Statistiques pour le dashboard
    try:
        stats = {
            'total_media': Media.objects.filter(user=request.user).count(),
            'total_images': Media.objects.filter(user=request.user, media_type='image').count(),
            'total_videos': Media.objects.filter(user=request.user, media_type='video').count(),
            'total_analyzed': Media.objects.filter(user=request.user, is_analyzed=True).count(),
            'total_favorites': Media.objects.filter(user=request.user, is_favorite=True).count(),
        }
    except Exception as e:
        print(f"Erreur stats: {e}")
        stats = {
            'total_media': 0,
            'total_images': 0,
            'total_videos': 0,
            'total_analyzed': 0,
            'total_favorites': 0,
        }
    
    # Pagination
    paginator = Paginator(media_list, 12)  # 12 médias par page
    page_number = request.GET.get('page')
    media_page = paginator.get_page(page_number)
    
    context = {
        'media_list': media_page,
        'filter_form': filter_form,
        'stats': stats,
        'view_mode': request.GET.get('view', 'grid'),  # grid ou list
    }
    
    return render(request, 'gallery.html', context)


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
                user_categories = Category.objects.filter(user=request.user)
                context = {
                    'single_form': MediaUploadForm(),
                    'multiple_form': MultipleMediaUploadForm(user=request.user),
                    'categories': user_categories,
                }
                return render(request, 'media_upload.html', context)
            
            # Validation de la catégorie
            if not category_id:
                messages.error(request, '❌ Vous devez sélectionner une catégorie.')
                user_categories = Category.objects.filter(user=request.user)
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
                user_categories = Category.objects.filter(user=request.user)
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
                user_categories = Category.objects.filter(user=request.user)
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
                user_categories = Category.objects.filter(user=request.user)
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
                    user_categories = Category.objects.filter(user=request.user)
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
                    user_categories = Category.objects.filter(user=request.user)
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
    
    # Récupérer les catégories de l'utilisateur connecté
    user_categories = Category.objects.filter(user=request.user)
    
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
                    'categories': Category.objects.filter(user=request.user),
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
        'categories': Category.objects.filter(user=request.user),
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
                return redirect('category_management')  # Redirect to category_management after login
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
    categories = Category.objects.filter(user=request.user)
    selected_category_id = request.GET.get('category_id')

    context = {
        'categories': categories,
        'selected_category_id': selected_category_id,
    }
    return render(request, 'view_notes.html', context)

@login_required
def add_note(request):
    return render(request, 'create_note.html')

@login_required
def tag_create(request):
    return render(request, 'tags.html')

@login_required
def event_create(request):
    return render(request, 'create_note.html')
