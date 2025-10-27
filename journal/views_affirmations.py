from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count 

from .models import Affirmation
from .forms import AffirmationForm
from .ai_affirmations import personalized_generate
from django.http import JsonResponse
from django.template.loader import render_to_string

TONE_CHOICES = [
    ('calm', 'Calm'),
    ('motivational', 'Motivational'),
    ('self_compassion', 'Self-Compassion'),
    ('focus', 'Focus'),
    ('confidence', 'Confidence'),
]
TONE_TO_LABEL = {k: v for k, v in TONE_CHOICES}

def _user_corpus(request):
    # Build minimal personalization from user's own affirmations (safe, no schema change)
    corpus = list(Affirmation.objects.filter(user=request.user).values_list("text", flat=True)[:50])
    return corpus

@login_required
def affirmation_list(request):
    q = request.GET.get("q", "")
    tone = request.GET.get("tone", "")
    topic = request.GET.get("topic", "").strip()

    # --- filtering section ---
    qs = Affirmation.objects.filter(user=request.user).order_by("-created_at")
    if q:
        qs = qs.filter(Q(text__icontains=q) | Q(topic__icontains=q))
    if tone:
        qs = qs.filter(tone=tone)
    if topic:
        qs = qs.filter(topic__icontains=topic)

    # --- KPI section (ADD THIS BLOCK HERE) ---
    total = Affirmation.objects.filter(user=request.user).count()
    tone_counts_raw = (Affirmation.objects
                       .filter(user=request.user)
                       .values('tone')
                       .annotate(c=Count('id')))

    # build list for easier template rendering
    tone_kpis = [(TONE_TO_LABEL.get(row['tone'], row['tone']), row['c'])
                 for row in tone_counts_raw]

    # --- context ---
    ctx = {
        "items": qs,
        "q": q,
        "tone": tone,
        "topic": topic,
        "total": total,
        "tone_kpis": tone_kpis,
        "tone_labels": {"choices": TONE_CHOICES, "tone_to_label": TONE_TO_LABEL},
    }

    return render(request, "affirmations_list.html", ctx)


@login_required
def affirmation_new(request):
    form = AffirmationForm(request.POST or None)
    is_modal = request.GET.get("modal") == "1" or request.POST.get("modal") == "1"

    if request.method == "POST":
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Affirmation ajoutée.")
            if is_modal or request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": True})
            return redirect("affirmation_list")
        else:
            # validation errors
            if is_modal or request.headers.get("x-requested-with") == "XMLHttpRequest":
                html = render_to_string("template/affirmations_form.html", {"form": form}, request=request)
                return JsonResponse({"ok": False, "html": html})

    # GET
    if is_modal or request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "affirmations_form.html", {"form": form})
    return render(request, "affirmations_form.html", {"form": form})


@login_required
def affirmation_edit(request, pk):
    obj = get_object_or_404(Affirmation, pk=pk, user=request.user)
    form = AffirmationForm(request.POST or None, instance=obj)

    # detect modal/ajax
    is_modal = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.GET.get("modal") == "1"
    )

    if request.method == "POST":
        if form.is_valid():
            form.save()
            if is_modal:
                return JsonResponse({"ok": True})
            messages.success(request, "Affirmation updated.")
            return redirect("affirmation_list")

    # GET or invalid POST
    if is_modal:
        return render(request, "affirmations_form_partial.html", {"form": form})
    return render(request, "affirmations_form.html", {"form": form, "is_new": False})   


@login_required
def affirmation_delete(request, pk):
    """Delete an affirmation after confirm (only owner's items)."""
    obj = get_object_or_404(Affirmation, pk=pk, user=request.user)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Affirmation deleted.")
        return redirect("affirmation_list")
    return render(request, "affirmations_delete.html", {"item": obj})


@login_required
def affirmation_use(request, pk):
    """Display one affirmation nicely (you can copy/paste to notes, etc.)."""
    obj = get_object_or_404(Affirmation, pk=pk, user=request.user)
    return render(request, "affirmations_use.html", {"item": obj})


@login_required
def affirmation_suggest(request):
    if request.method == "POST":
        chosen = request.POST.getlist("chosen")
        tone = request.POST.get("tone", "calm")
        topic = (request.POST.get("topic") or "").strip()
        created = 0
        for text in chosen:
            text = (text or "").strip()
            if not text:
                continue
            if not Affirmation.objects.filter(user=request.user, text__iexact=text).exists():
                Affirmation.objects.create(user=request.user, text=text, tone=tone, topic=topic)
                created += 1
        if created:
            messages.success(request, f"Saved {created} affirmation(s) to your list.")
        else:
            messages.info(request, "Nothing saved (maybe duplicates or no selection).")
        return redirect("affirmation_list")

    # GET
    tone = request.GET.get("tone", "calm")
    topic = (request.GET.get("topic") or "").strip()
    style = request.GET.get("style", "concise")
    n = int(request.GET.get("n", 6))
    creativity = float(request.GET.get("creativity", 0.4))
    diversity = float(request.GET.get("diversity", 0.6))

    corpus = _user_corpus(request)
    suggestions = personalized_generate(
        user_texts=corpus,
        n=n,
        tone=tone,
        topic=topic or None,
        style=style,
        creativity=creativity,
        diversity=diversity,
    )

    have = set(Affirmation.objects.filter(user=request.user).values_list("text", flat=True))
    uniq = [s for s in suggestions if s not in have] or suggestions

    ctx = {"tone": tone, "topic": topic, "style": style, "n": n,
           "creativity": creativity, "diversity": diversity, "suggestions": uniq}
    return render(request, "affirmations_suggest.html", ctx)

@login_required
def affirmation_suggest_api(request):
    """Return JSON list of suggestions (no save)."""
    tone = request.GET.get("tone", "calm")
    topic = (request.GET.get("topic") or "").strip()
    style = request.GET.get("style", "concise")
    n = int(request.GET.get("n", 6))
    creativity = float(request.GET.get("creativity", 0.4))
    diversity = float(request.GET.get("diversity", 0.6))

    corpus = _user_corpus(request)
    data = personalized_generate(
        user_texts=corpus,
        n=n, tone=tone, topic=topic or None, style=style, creativity=creativity, diversity=diversity
    )
    return JsonResponse({"items": data})

@login_required
def affirmation_paraphrase_one(request):
    """Return JSON with a single re-rolled suggestion."""
    tone = request.GET.get("tone", "calm")
    topic = (request.GET.get("topic") or "").strip()
    style = request.GET.get("style", "concise")
    creativity = float(request.GET.get("creativity", 0.6))  # a bit higher for re-roll
    diversity = float(request.GET.get("diversity", 0.6))

    corpus = _user_corpus(request)
    data = personalized_generate(
        user_texts=corpus, n=5, tone=tone, topic=topic or None,
        style=style, creativity=creativity, diversity=diversity
    )
    return JsonResponse({"text": data[0] if data else ""})