"""
Vues pour la gestion des albums intelligents
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import SmartAlbum, Media
from .services.smart_album_service import smart_album_service
import json


@login_required
def smart_albums_list(request):
    """Liste tous les albums intelligents de l'utilisateur"""
    
    # Albums automatiques - select_related pour cover_image uniquement
    auto_albums = SmartAlbum.objects.filter(
        user=request.user,
        album_type='auto'
    ).select_related('cover_image')
    
    # Albums manuels
    manual_albums = SmartAlbum.objects.filter(
        user=request.user,
        album_type='manual'
    ).select_related('cover_image')
    
    # Suggestions d'albums potentiels
    suggestions = smart_album_service.get_album_suggestions(request.user)
    
    context = {
        'auto_albums': auto_albums,
        'manual_albums': manual_albums,
        'suggestions': suggestions,
        'total_auto': auto_albums.count(),
        'total_manual': manual_albums.count(),
    }
    
    return render(request, 'smart_albums_list.html', context)


@login_required
def album_detail(request, album_id):
    """Détail d'un album avec ses médias"""
    album = get_object_or_404(SmartAlbum, id=album_id, user=request.user)
    
    # Récupérer tous les médias de l'album
    media_list = album.media.all().order_by('-uploaded_at')
    
    context = {
        'album': album,
        'media_list': media_list,
        'media_count': media_list.count(),
    }
    
    return render(request, 'album_detail.html', context)


@login_required
@require_POST
def create_auto_albums(request):
    """Créer automatiquement tous les albums intelligents"""
    
    try:
        force_recreate = request.POST.get('force_recreate') == 'true'
        
        # Créer les albums
        stats = smart_album_service.create_all_smart_albums(
            user=request.user,
            force_recreate=force_recreate
        )
        
        # Message de succès
        if stats['created'] > 0 or stats['updated'] > 0:
            messages.success(
                request,
                f"✨ {stats['created']} albums créés, {stats['updated']} mis à jour!"
            )
        else:
            messages.info(
                request,
                "ℹ️ Aucun album n'a pu être créé. Analysez plus de photos d'abord!"
            )
        
        return redirect('smart_albums_list')
        
    except Exception as e:
        messages.error(request, f"❌ Erreur: {str(e)}")
        return redirect('smart_albums_list')


@login_required
@require_POST
def update_album(request, album_id):
    """Met à jour un album automatique"""
    
    try:
        album = smart_album_service.update_album(album_id)
        
        if album:
            messages.success(
                request,
                f"✅ Album '{album.name}' mis à jour! ({album.media.count()} médias)"
            )
        else:
            messages.error(request, "❌ Impossible de mettre à jour cet album")
        
        return redirect('album_detail', album_id=album_id)
        
    except Exception as e:
        messages.error(request, f"❌ Erreur: {str(e)}")
        return redirect('smart_albums_list')


@login_required
@require_POST
def delete_album(request, album_id):
    """Supprime un album"""
    
    try:
        album = get_object_or_404(SmartAlbum, id=album_id, user=request.user)
        album_name = album.name
        album.delete()
        
        messages.success(request, f"✅ Album '{album_name}' supprimé")
        return redirect('smart_albums_list')
        
    except Exception as e:
        messages.error(request, f"❌ Erreur: {str(e)}")
        return redirect('smart_albums_list')


@login_required
@require_POST
def create_manual_album(request):
    """Créer un album manuel"""
    
    try:
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, "❌ Le nom de l'album est requis")
            return redirect('smart_albums_list')
        
        # Créer l'album
        album = SmartAlbum.objects.create(
            user=request.user,
            name=name,
            description=description,
            album_type='manual'
        )
        
        messages.success(request, f"✅ Album '{name}' créé!")
        return redirect('album_detail', album_id=album.id)
        
    except Exception as e:
        messages.error(request, f"❌ Erreur: {str(e)}")
        return redirect('smart_albums_list')


@login_required
@require_POST
def add_media_to_album(request, album_id):
    """Ajouter des médias à un album"""
    
    try:
        album = get_object_or_404(SmartAlbum, id=album_id, user=request.user)
        
        # Récupérer les IDs des médias
        media_ids = request.POST.getlist('media_ids[]')
        
        if not media_ids:
            messages.warning(request, "⚠️ Aucun média sélectionné")
            return redirect('album_detail', album_id=album_id)
        
        # Ajouter les médias
        media_objects = Media.objects.filter(
            id__in=media_ids,
            user=request.user
        )
        
        album.media.add(*media_objects)
        
        messages.success(
            request,
            f"✅ {len(media_ids)} médias ajoutés à l'album '{album.name}'"
        )
        
        return redirect('album_detail', album_id=album_id)
        
    except Exception as e:
        messages.error(request, f"❌ Erreur: {str(e)}")
        return redirect('smart_albums_list')


@login_required
@require_POST
def remove_media_from_album(request, album_id, media_id):
    """Retirer un média d'un album"""
    
    try:
        album = get_object_or_404(SmartAlbum, id=album_id, user=request.user)
        media = get_object_or_404(Media, id=media_id, user=request.user)
        
        album.media.remove(media)
        
        messages.success(request, f"✅ Média retiré de l'album '{album.name}'")
        return redirect('album_detail', album_id=album_id)
        
    except Exception as e:
        messages.error(request, f"❌ Erreur: {str(e)}")
        return redirect('album_detail', album_id=album_id)


@login_required
def album_suggestions_json(request):
    """API JSON pour récupérer les suggestions d'albums"""
    
    try:
        suggestions = smart_album_service.get_album_suggestions(request.user)
        
        return JsonResponse({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
