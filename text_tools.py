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
    "prompt": "A melancholic post-punk track with angular guitar riffs, driving bass, and brooding baritone vocals. Features cold synth textures, mechanical drums, and a dark atmospheric production style.",
    "lyrics": """[Intro]

[Verse 1]
Fluorescent lights flicker and fade
Another night another masquerade
Faces blur in the crowded room
Dancing slowly toward our doom

[Verse 2]
Conversations without meaning
Smiles that hide the silent screaming
We perform our daily roles
Empty vessels hollow souls

[Chorus]
We're all just ghosts in the machine
Going through motions in between
Searching for something that feels real
Something that we can truly feel

[Verse 3]
Concrete towers touch the sky
Millions living asking why
Connected yet so far apart
Lonely beats of every heart

[Chorus]
We're all just ghosts in the machine
Going through motions in between

[Outro]
Ghosts in the machine"""
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


def is_probably_french(text: str) -> bool:
    sample = re.sub(r"\[[^]]+\]", "", text).strip()
    if len(sample) < 18:
        return False
    try:
        return detect(sample) == "fr"
    except LangDetectException:
        return False


def translate_to_english(text: str, *, force: bool = False, preserve_sections: bool = False) -> tuple[str, bool]:
    """Traduction via un service tiers ; aucune clé musicale n'est transmise."""
    if not text.strip():
        return text, False
    if not force and not is_probably_french(text):
        return text, False
    translator = GoogleTranslator(source="auto", target="en")
    if not preserve_sections:
        translated = translator.translate(text[:4500])
        if len(text) > 4500:
            raise ValueError("La description dépasse la longueur prise en charge pour la traduction.")
        if not translated:
            raise ValueError("Le traducteur n'a pas retourné de texte.")
        return translated, True
    # Conserver exactement les balises [Verse 1], [Chorus], [Intro], etc.
    result: list[str] = []
    fragments = text.splitlines(keepends=True)
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        source = "".join(buffer)
        if source.strip():
            # 4000 caractères par appel, tout en maintenant le groupe de vers.
            translated = translator.translate(source[:4500])
            if len(source) > 4500:
                raise ValueError("Un couplet est trop long pour le service de traduction.")
            if not translated:
                raise ValueError("Traduction indisponible.")
            result.append(translated.strip() + "\n")
        buffer.clear()

    for line in fragments:
        if TAG_PATTERN.match(line):
            flush()
            result.append(line.rstrip("\r\n") + "\n")
        elif not line.strip():
            flush()
            result.append("\n")
        else:
            buffer.append(line)
    flush()
    return "".join(result).strip(), True


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
