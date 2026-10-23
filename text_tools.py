"""Outils de rédaction, traduction FR→EN et structure des paroles."""
from __future__ import annotations

import random
import re
from dataclasses import dataclass

from deep_translator import GoogleTranslator
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


def translate_to_english(text: str, *, force: bool = False, preserve_sections: bool = False) -> tuple[str, bool]:
    """Préparation linguistique idiomatique des contenus transmis au moteur.

    Les balises de structure et la mise en vers restent inchangées.
    Les saisies déjà anglaises sont utilisées telles quelles.
    """
    if not text.strip():
        return text, False
    if not force and not is_probably_french(text):
        return text, False
    translator = GoogleTranslator(source="auto", target="en")

    def translate_passage(source: str) -> str:
        if len(source) > 4500:
            raise ValueError("Texte trop long pour le traitement linguistique.")
        result = translator.translate(source)
        if not result or not result.strip():
            raise ValueError("Le traitement linguistique n'a pas abouti.")
        return _natural_musical_english(result.strip())

    if not preserve_sections:
        return translate_passage(text), True

    # Chaque section est traitée en conservant le contexte du couplet, puis ses
    # lignes : un changement de mise en forme du traducteur ne doit pas fusionner
    # des vers qui doivent être chantés séparément.
    translated: list[str] = []
    stanza: list[str] = []

    def flush_stanza() -> None:
        if not stanza:
            return
        source = "\n".join(stanza)
        if not force and not is_probably_french(source):
            translated.extend(stanza)
        else:
            candidate = translate_passage(source)
            candidate_lines = candidate.splitlines()
            if len(candidate_lines) == len(stanza) and all(line.strip() for line in candidate_lines):
                translated.extend(line.strip() for line in candidate_lines)
            else:
                translated.extend(translate_passage(line) for line in stanza)
        stanza.clear()

    for line in text.splitlines():
        if TAG_PATTERN.fullmatch(line):
            flush_stanza()
            translated.append(line.strip())
        elif not line.strip():
            flush_stanza()
            translated.append("")
        else:
            stanza.append(line)
    flush_stanza()
    return "\n".join(translated).strip(), True


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
