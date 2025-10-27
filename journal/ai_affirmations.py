# journal/ai_affirmations.py
import math
import random
import re
from collections import Counter
from itertools import combinations

# -------------------- tone bank (same as before, trimmed for brevity) --------------------
TONE_BANK = {
    "calm": {
        "open": ["Je respire, je me calme et", "Avec un souffle tranquille,", "À cet instant,", "Je m’accueille avec douceur et"],
        "verbs": ["j’autorise", "j’accueille", "je choisis", "je reviens à", "je fais confiance à"],
        "close": ["un sentiment de paix.", "une confiance tranquille.", "l’espace dont j’ai besoin.", "ce que je peux contrôler.", "le rythme qui me convient."],
    },
    "motivational": {
        "open": ["Aujourd’hui, je décide de", "Je me lève et je", "Pas à pas, je", "Je m’engage à"],
        "verbs": ["avancer avec", "construire", "créer", "embrasser", "agir avec"],
        "close": ["une progression constante.", "le prochain bon pas.", "un élan que je ressens.", "du courage et de la clarté.", "des résultats à mon image."],
    },
    "self_compassion": {
        "open": ["Je me traite avec", "Je m’offre", "J’accueille mes échecs avec", "Je suis digne de"],
        "verbs": ["gentillesse et", "patience et", "compréhension et", "respect et"],
        "close": ["un nouveau départ.", "une voix plus douce.", "du temps pour apprendre.", "des soins à mon rythme.", "de la grâce, même dans l’imperfection."],
    },
    "focus": {
        "open": ["Je concentre mon attention sur", "Je ramène mon esprit vers", "Je simplifie et choisis", "Je protège du temps pour"],
        "verbs": ["la tâche essentielle,", "des priorités claires et", "un travail profond et", "une exécution régulière et"],
        "close": ["des progrès sans distraction.", "la qualité avant la vitesse.", "un résultat dont je suis fier.", "de la clarté dans l’action."],
    },
    "confidence": {
        "open": ["Je fais confiance à ma capacité de", "Je suis capable et je", "Je me soutiens pour", "J’apporte de la valeur en"],
        "verbs": ["apprendre vite et", "trouver des solutions et", "agir avec", "parler avec"],
        "close": ["une présence authentique.", "des preuves par mes actions.", "une force tranquille.", "des résultats qui s’accumulent."],
    },
}

STYLE_PREFIX = {"concise": "", "gentle": "Gently, ", "bold": "With conviction, "}

def _clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if s.endswith((".", "!", "?")) else s + "."

def _with_topic(base: str, topic: str | None) -> str:
    if not topic:
        return base
    choices = [f"{base} in {topic}", f"{base} around {topic}", f"{base} for {topic}", f"{base} as I work on {topic}"]
    return random.choice(choices)

# -------------------- tiny NLP helpers (local, no heavy deps) --------------------
STOP = set("""
a an the and or of on in to for with at from as into about by over under up down out off than then so such very really just more most
i me my mine you your yours we our ours they them their theirs he she it its is are am be being been was were do does did doing have has had
""".split())

def tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[a-zA-Z][a-zA-Z\-']+", text)]

def keywords_from_texts(texts: list[str], k: int = 10) -> list[str]:
    cnt = Counter()
    for t in texts:
        for tok in tokenize(t):
            if tok not in STOP and len(tok) > 2:
                cnt[tok] += 1
    return [w for w, _ in cnt.most_common(k)]

def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b.get(t, 0) for t in a)
    na = math.sqrt(sum(v*v for v in a.values()))
    nb = math.sqrt(sum(v*v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0

def bow(text: str) -> Counter:
    return Counter([t for t in tokenize(text) if t not in STOP])

def mmr_select(cands: list[str], user_bow: Counter, lam: float = 0.7, k: int = 5) -> list[str]:
    """Maximal Marginal Relevance: balance relevance (to user) and diversity (vs already picked)."""
    selected: list[str] = []
    cand_bows = {c: bow(c) for c in cands}
    while cands and len(selected) < k:
        best, best_score = None, -1
        for c in cands:
            rel = cosine(cand_bows[c], user_bow)
            div = 0.0
            if selected:
                div = max(1 - cosine(cand_bows[c], cand_bows[s]) for s in selected)
            score = lam * rel + (1 - lam) * div
            if score > best_score:
                best, best_score = c, score
        selected.append(best)
        cands.remove(best)
    return selected

# -------------------- core API --------------------
def base_generate(n: int = 8, tone: str = "calm", topic: str | None = None, style: str = "concise", creativity: float = 0.4) -> list[str]:
    tone = tone if tone in TONE_BANK else "calm"
    bank = TONE_BANK[tone]
    results: set[str] = set()
    prefix = STYLE_PREFIX.get(style, "")

    # creativity = how often we pick rare combos
    # 0.0 → very safe; 1.0 → more mix
    def pick(arr):  # weighted pick
        if creativity <= 0.15:
            return arr[0 if arr else 0] if arr else ""
        idx = int(random.random() ** (1 - creativity) * (len(arr) - 1))
        return arr[min(idx, len(arr)-1)]

    tries = 0
    while len(results) < n and tries < n * 12:
        tries += 1
        open_part = pick(bank["open"])
        verb = pick(bank["verbs"])
        close_part = pick(bank["close"])
        mid = f"{verb} {_with_topic(close_part, topic)}"
        sentence = _clean(f"{prefix}{open_part} {mid}")
        results.add(sentence)

    return list(results)[:n]

def personalized_generate(
    user_texts: list[str] | None,
    n: int = 8,
    tone: str = "calm",
    topic: str | None = None,
    style: str = "concise",
    creativity: float = 0.4,
    diversity: float = 0.6,
) -> list[str]:
    """
    - user_texts: recent affirmations and (if you decide) notes (strings)
    - diversity: 0..1, how much to diversify vs only relevance
    """
    # 1) base candidates
    cands = base_generate(n=max(n*2, 10), tone=tone, topic=topic, style=style, creativity=creativity)

    # 2) build user profile bow
    user_b = Counter()
    if user_texts:
        for t in user_texts:
            user_b.update(bow(t))
    # Also add topic tokens to bias if provided
    if topic:
        user_b.update(bow(topic))

    # 3) select via MMR (relevance to user_b + diversity between candidates)
    lam = max(0.2, min(0.9, 1 - diversity))  # invert: higher diversity → lower lambda
    if sum(user_b.values()) == 0:
        # no user signals, just dedup + first n
        seen = set()
        out = []
        for c in cands:
            key = re.sub(r"[^a-zA-Z]+", "", c.lower())
            if key in seen: 
                continue
            seen.add(key)
            out.append(c)
            if len(out) >= n:
                break
        return out
    else:
        return mmr_select(cands[:], user_b, lam=lam, k=n)
