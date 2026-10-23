"""Outils de rédaction, traduction FR→EN et structure des paroles."""
from __future__ import annotations

import random
import re
import time
from html import unescape

import requests
from langdetect import DetectorFactory, detect, LangDetectException

DetectorFactory.seed = 0

SECTIONS = ("Intro", "Verse 1", "Verse 2", "Chorus", "Verse 3", "Bridge", "Chorus", "Outro")
TAG_PATTERN = re.compile(r"^\s*\[[^\]\n]+\]\s*$")

EXAMPLES = {
    "prompt": "Une chanson country chaleureuse et entraînante, portée par une guitare acoustique, une pedal steel guitar, une basse ronde et une batterie légère. Voix masculine grave et chaleureuse, mélodie mémorable, ambiance de route au coucher du soleil, son organique et authentique.",
    "lyrics": """[Intro]

[Verse 1]
Le vieux moteur gronde au petit matin
Sur la route qui traverse les sapins
Le soleil embrase les collines
Et le vent me souffle une mélodie

[Verse 2]
J'ai laissé la ville et ses lumières
Pour retrouver le goût de la poussière
Un café chaud sur le tableau de bord
Et mille kilomètres à rêver encore

[Chorus]
Sur la route, le cœur en liberté
Je laisse les soucis s'envoler
Sous le grand ciel et les étoiles
Je trace ma route, je mets les voiles

[Verse 3]
Dans le rétroviseur, tant de souvenirs
Les petites routes où l'on aimait rire
Chaque virage m'offre un horizon
Et les mêmes accords, une chanson

[Chorus]
Sur la route, le cœur en liberté
Je laisse les soucis s'envoler
Sous le grand ciel et les étoiles
Je trace ma route, je mets les voiles

[Outro]
Un dernier soleil sur le chemin
Et la musique jusqu'à demain"""
}

MOODS = {
    "Nostalgique": (
        ["La ville s'endort derrière les vitres", "Les souvenirs reviennent à pas feutrés", "Dans le silence je cherche une trace", "Le passé dessine encore nos visages"],
        ["Il reste une lumière au fond de nous", "Même si les jours effacent tout", "Je garde un peu de ce qu'on était", "Comme un refrain qui ne veut pas s'arrêter"],
    ),
    "Joyeux": (
        ["Le soleil nous invite à partir", "Nos pas inventent de nouveaux chemins", "Le vent nous donne envie de sourire", "Demain se construit entre nos mains"],
        ["Alors viens, on danse jusqu'au matin", "Tout est possible au bout du chemin", "Nos voix s'élèvent sous le ciel immense", "Cette nuit, la vie nous appartient"],
    ),
    "Épique": (
        ["Au loin les montagnes se réveillent", "Un nouvel horizon surgit de l'ombre", "Le courage traverse les frontières", "Et nos voix résonnent sur la terre"],
        ["Plus haut que nos peurs et nos regrets", "Nous avançons sans jamais céder", "Que le tonnerre éclaire notre histoire", "Nos rêves écrivent enfin la victoire"],
    ),
    "Mélancolique": (
        ["Sous les néons les ombres se croisent", "Les mots se perdent dans le bruit du soir", "Chaque fenêtre cache une histoire", "Un cœur attend derrière le miroir"],
        ["On cherche encore un peu de lumière", "Au milieu de ce monde à l'envers", "Et sous le poids de toutes nos absences", "On garde un espoir dans le silence"],
    ),
}


_FRENCH_MARKERS = {
    "avec", "sans", "une", "des", "dans", "pour", "les", "aux", "sur",
    "comme", "chanson", "musique", "chant", "voix", "guitare",
    "guitares", "batterie", "violon", "refrain", "couplet", "rythme",
    "douce", "doux", "joyeux", "joyeuse", "mélancolique", "entraînant",
    "entraînante", "grave", "chaude", "chaleureuse", "acoustique",
    "électrique", "je", "tu", "nous", "mon", "ma", "mes", "notre", "le",
    "la", "un", "est", "sont", "être", "qui", "que", "me", "te",
}
_MUSICAL_MARKERS = {
    "chanson", "musique", "voix", "guitare", "guitares", "batterie",
    "violon", "refrain", "couplet", "rythme", "acoustique", "entraînante",
    "électrique",
}


def is_probably_french(text: str) -> bool:
    """Reconnaît aussi des prompts français très courts, sans altérer l'anglais."""
    sample = re.sub(r"\[[^\n\]]+\]", "", text).strip()
    if not sample:
        return False
    words = [w.lower() for w in re.findall(r"[A-Za-zÀ-ÿœŒ]+", sample)]
    markers = sum(word in _FRENCH_MARKERS for word in words)
    if re.search(r"[àâçéèêëîïôùûüÿœ]", sample.lower()):
        return True
    if markers >= 2 or any(word in _MUSICAL_MARKERS for word in words):
        return True
    try:
        return detect(sample) == "fr"
    except LangDetectException:
        return False


def _natural_musical_english(text: str) -> str:
    """Adapte quelques tournures fréquentes aux conventions des prompts musicaux."""
    substitutions = (
        (r"\ba country music\b", "a country song"),
        (r"\ba music of the country style\b", "a country song"),
        (r"\ba serious male voice\b", "a deep male voice"),
        (r"\ba grave male voice\b", "rich baritone vocals"),
        (r"\ba deep and warm male voice\b", "warm baritone vocals"),
        (r"\ba deep male voice\b", "deep male vocals"),
        (r"\ba driving battery\b", "driving drums"),
        (r"\bsoft battery\b", "gentle drums"),
        (r"\bround bass\b", "warm, rounded bass"),
        (r"\bvery rhythmic\b", "driving and rhythmic"),
        (r"\ba warm and warm\b", "warm"),
    )
    for source, target in substitutions:
        text = re.sub(source, target, text, flags=re.IGNORECASE)
    return text


class TranslationUnavailable(ValueError):
    """Le texte n'a pas pu être préparé dans le délai imparti."""


_TRANSLATION_SECONDS = 15.0
_GOOGLE_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
_MEMORY_ENDPOINT = "https://api.mymemory.translated.net/get"


def _translated_french(text: str) -> bool:
    """Contrôle conservateur des résultats manifestement restés en français."""
    if len(text.strip()) < 12:
        return False
    try:
        return detect(text) == "fr"
    except LangDetectException:
        return False


def _translate_network(source: str, deadline: float, target: str = "en") -> str:
    """Deux fournisseurs publics ; un délai global est partagé par les appels.

    L'API Google utilisée est non officielle : si elle change, le second
    fournisseur est sollicité sans nouvelle intervention de l'utilisateur.
    """
    if not source.strip():
        return source
    if len(source) > 4500:
        raise TranslationUnavailable("Le texte est trop long pour être préparé.")
    errors = []
    for provider in ("google", "mymemory"):
        left = deadline - time.monotonic()
        if left <= 0.8:
            break
        try:
            timeout = (min(2.0, left / 2), min(4.5, max(1.0, left - 0.4)))
            if provider == "google":
                response = requests.get(
                    _GOOGLE_ENDPOINT,
                    params={"client": "gtx", "sl": "fr", "tl": target, "dt": "t", "q": source},
                    timeout=timeout,
                )
                response.raise_for_status()
                data = response.json()
                candidate = "".join(
                    segment[0] for segment in data[0]
                    if isinstance(segment, list) and segment and isinstance(segment[0], str)
                )
            else:
                if len(source) > 480:
                    continue
                response = requests.get(
                    _MEMORY_ENDPOINT,
                    params={"q": source, "langpair": f"fr|{target}"},
                    timeout=timeout,
                )
                response.raise_for_status()
                data = response.json()
                if int(data.get("responseStatus", 200)) != 200:
                    raise ValueError("Service translation unavailable")
                candidate = unescape(str(data.get("responseData", {}).get("translatedText") or ""))
            candidate = candidate.strip()
            if not candidate or _translated_french(candidate):
                raise ValueError("Réponse non traduite")
            return _natural_musical_english(candidate) if target == "en" else candidate
        except (requests.RequestException, ValueError, KeyError, TypeError, IndexError) as exc:
            errors.append(type(exc).__name__)
    raise TranslationUnavailable(
        "La préparation du texte est momentanément indisponible. "
        "Tu peux essayer plus tard, ou saisir une description en anglais."
    )


def translate_to_language(
    text: str,
    target: str = "en",
    *,
    force: bool = False,
    preserve_sections: bool = False,
) -> tuple[str, bool]:
    """Prépare la description/les paroles en anglais sans altérer les balises.

    Un seul délai global de 15 s évite les attentes cumulées de plusieurs
    traducteurs. Ne prétend jamais avoir traduit un texte si le réseau échoue.
    """
    if target not in ("fr", "en", "es", "de", "it", "pt"):
        raise ValueError("Langue non reconnue.")
    if not text.strip() or target == "fr":
        return text, False
    if not force and not is_probably_french(text):
        return text, False
    deadline = time.monotonic() + _TRANSLATION_SECONDS
    if not preserve_sections:
        return _translate_network(text, deadline, target), True

    lines = text.splitlines()
    content_indexes = [
        i for i, line in enumerate(lines)
        if line.strip() and not TAG_PATTERN.fullmatch(line)
    ]
    if not content_indexes:
        return text, False
    translatable_indexes = [
        i for i in content_indexes if force or is_probably_french(lines[i])
    ]
    if not translatable_indexes:
        return text, False

    # Une seule requête pour conserver le contexte de la chanson.
    source = "\n".join(lines[i] for i in content_indexes)
    try:
        result = _translate_network(source, deadline, target)
        result_lines = result.splitlines()
        if len(result_lines) == len(content_indexes) and all(x.strip() for x in result_lines):
            for i, translated in zip(content_indexes, result_lines):
                lines[i] = translated.strip()
            return "\n".join(lines), True
    except TranslationUnavailable:
        pass

    # Si le fournisseur a fusionné les lignes, retraiter par strophe (un
    # traducteur supplémentaire par ligne serait excessivement lent).
    groups = []
    active = []
    for i, line in enumerate(lines):
        if not line.strip() or TAG_PATTERN.fullmatch(line):
            if active:
                groups.append(active)
                active = []
        else:
            active.append(i)
    if active:
        groups.append(active)
    for group in groups:
        if not any(i in translatable_indexes for i in group):
            continue
        left = deadline - time.monotonic()
        if left <= 0.8:
            raise TranslationUnavailable("La préparation des paroles a dépassé son délai.")
        translated = _translate_network("\n".join(lines[i] for i in group), deadline, target)
        translated_lines = translated.splitlines()
        if len(translated_lines) != len(group):
            raise TranslationUnavailable(
                "Impossible de conserver correctement la structure des paroles. "
                "Réessaie plus tard."
            )
        for i, value in zip(group, translated_lines):
            lines[i] = value.strip()
    return "\n".join(lines), True


def translate_to_english(
    text: str,
    *,
    force: bool = False,
    preserve_sections: bool = False,
) -> tuple[str, bool]:
    """Prépare un texte français en anglais pour la description musicale."""
    return translate_to_language(
        text, target="en", force=force, preserve_sections=preserve_sections
    )


def structure_lyrics(text: str) -> str:
    """Structure une ébauche saisie librement sans réécrire son contenu."""
    text = text.strip()
    if not text:
        return ""
    if re.search(r"(?im)^\s*\[(intro|verse|chorus|bridge|outro)", text):
        return text
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return ""
    titles = ["Verse 1", "Chorus", "Verse 2", "Chorus", "Bridge", "Chorus", "Outro"]
    return "\n\n".join(f"[{titles[min(i,len(titles)-1)]}]\n{p}" for i, p in enumerate(paragraphs))


def draft_lyrics(brief: str, mood: str = "Nostalgique") -> str:
    """Ébauche LOCALE par gabarits; ne se présente jamais comme de l'IA."""
    brief = re.sub(r"\s+", " ", brief).strip().strip(".!?")
    if not brief:
        raise ValueError("Décris d'abord le thème de ta chanson.")
    # Le thème saisi sert de fil conducteur sans inventer des faits.
    theme = brief[:76]
    verse, chorus = MOODS.get(mood, MOODS["Nostalgique"])
    rng = random.Random()
    v1 = rng.sample(verse, min(4, len(verse)))
    v2 = rng.sample(verse, min(4, len(verse)))
    refrain = list(chorus)
    return (
        "[Intro]\n(instrumental)\n\n"
        f"[Verse 1]\n{v1[0]}\n{v1[1]}\n"
        f"Tout me ramène à {theme.lower()}\n{v1[2]}\n\n"
        f"[Verse 2]\n{v2[1]}\n{v2[2]}\n"
        f"Je pense encore à {theme.lower()}\n{v2[3]}\n\n"
        "[Chorus]\n" + "\n".join(refrain) + "\n\n"
        f"[Verse 3]\n{v1[3]}\n{v2[0]}\n"
        f"Un jour je comprendrai {theme.lower()}\n{v1[1]}\n\n"
        "[Chorus]\n" + "\n".join(refrain) + "\n\n"
        f"[Outro]\n{refrain[0]}\n{refrain[1]}"
    )
