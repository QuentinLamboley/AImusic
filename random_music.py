"""Inspiration musicale aléatoire, sans appel externe.

La description visible est française ; son équivalent musical est préparé
en anglais, avec les mêmes attributs, pour l'API de génération.
"""
from __future__ import annotations

import secrets


STYLES = (
    ("country folk", "country-folk", "acoustic guitars and pedal steel", "guitares acoustiques et pedal steel"),
    ("soul rétro", "vintage soul", "expressive electric piano, a warm bassline and horns", "piano électrique expressif, basse chaleureuse et cuivres"),
    ("rock indépendant", "indie rock", "jangly electric guitars, live drums and melodic bass", "guitares électriques cristallines, batterie acoustique et basse mélodique"),
    ("jazz nocturne", "late-night jazz", "intimate piano, brushed drums and double bass", "piano intimiste, batterie aux balais et contrebasse"),
    ("funk", "funk", "syncopated rhythm guitar, punchy bass and brass accents", "guitare rythmique syncopée, basse percutante et accents de cuivres"),
    ("pop synthétique", "synth-pop", "analog synthesizers, shimmering pads and electronic drums", "synthétiseurs analogiques, nappes lumineuses et batterie électronique"),
    ("bossa nova", "bossa nova", "soft nylon-string guitar, gentle percussion and warm bass", "guitare nylon douce, percussions légères et basse ronde"),
    ("blues du Delta", "Delta blues", "fingerpicked acoustic guitar, slide guitar and understated percussion", "guitare acoustique en fingerpicking, slide guitar et percussions discrètes"),
    ("disco", "disco", "four-on-the-floor drums, rhythmic strings and a lively bassline", "batterie dansante à quatre temps, cordes rythmiques et basse énergique"),
    ("chanson acoustique", "acoustic singer-songwriter", "fingerstyle guitar, delicate piano and subtle percussion", "guitare fingerstyle, piano délicat et percussions subtiles"),
    ("musique cinématique", "cinematic orchestral", "lush strings, grand piano, French horns and orchestral percussion", "cordes amples, piano à queue, cors et percussions orchestrales"),
    ("reggae", "roots reggae", "offbeat guitar, deep bass and relaxed drums", "guitare en contretemps, basse profonde et batterie détendue"),
    ("post-rock", "post-rock", "reverberant guitars, evolving textures and powerful live drums", "guitares réverbérées, textures évolutives et batterie acoustique puissante"),
    ("électro douce", "downtempo electronica", "ambient synth textures, warm sub-bass and intricate electronic percussion", "textures de synthétiseurs atmosphériques, basses profondes et percussions électroniques fines"),
)
MOODS = (
    ("nostalgique et chaleureuse", "nostalgic and warm"),
    ("joyeuse et pleine d'énergie", "joyful and energetic"),
    ("mystérieuse et enveloppante", "mysterious and immersive"),
    ("romantique et intimiste", "romantic and intimate"),
    ("lumineuse et optimiste", "bright and uplifting"),
    ("mélancolique mais pleine d'espoir", "melancholic yet hopeful"),
    ("cinématique et grandiose", "cinematic and expansive"),
    ("douce et apaisante", "gentle and soothing"),
    ("rythmée et festive", "rhythmic and celebratory"),
    ("rêveuse et aérienne", "dreamy and airy"),
)
THEMES = (
    ("un voyage sur une route de campagne", "a journey along a countryside road"),
    ("les souvenirs des vacances d'enfance", "memories of childhood holidays"),
    ("un amour qui traverse les années", "a love that lasts through the years"),
    ("une soirée d'été entre amis", "a summer evening with friends"),
    ("un atelier rempli de machines anciennes", "a workshop filled with vintage machines"),
    ("l'envie de prendre un nouveau départ", "the courage to make a fresh start"),
    ("une promenade à travers les montagnes", "a walk through the mountains"),
    ("une ville illuminée au milieu de la nuit", "a city glowing in the middle of the night"),
    ("les rêves d'aventure et de liberté", "dreams of adventure and freedom"),
    ("un instant de bonheur simple et précieux", "a simple, precious moment of happiness"),
    ("une dernière danse avant le matin", "one last dance before morning"),
    ("les retrouvailles après une longue absence", "a reunion after a long separation"),
    ("le calme après la tempête", "the calm after the storm"),
    ("une vieille photographie retrouvée", "an old photograph found again"),
)
VOCALS = (
    ("une voix masculine chaleureuse", "warm male vocals"),
    ("une voix féminine expressive", "expressive female vocals"),
    ("une voix grave et feutrée", "soft, low-register vocals"),
    ("des harmonies vocales à plusieurs voix", "layered vocal harmonies"),
    ("une interprétation vocale naturelle", "natural, heartfelt vocals"),
)
PRODUCTIONS = (
    ("une production chaleureuse et organique", "warm, organic production"),
    ("un mixage clair et spacieux", "a clean, spacious mix"),
    ("une ambiance d'enregistrement en direct", "the feel of a live studio performance"),
    ("une production soignée aux textures détaillées", "polished production with rich, detailed textures"),
)


def make_random_idea() -> dict[str, str]:
    """Une proposition complète et cohérente par tirage, sans requête API."""
    rng = secrets.SystemRandom()
    style_fr, style_en, inst_en, inst_fr = rng.choice(STYLES)
    mood_fr, mood_en = rng.choice(MOODS)
    theme_fr, theme_en = rng.choice(THEMES)
    vocal_fr, vocal_en = rng.choice(VOCALS)
    prod_fr, prod_en = rng.choice(PRODUCTIONS)
    return {
        "title": f"Surprise {style_fr}",
        "fr": (
            f"Une chanson {style_fr}, {mood_fr}, avec {inst_fr}, "
            f"{vocal_fr}. Le texte raconte {theme_fr}. "
            f"Ambiance musicale immersive, {prod_fr}."
        ),
        "en": (
            f"An original {style_en} song, {mood_en}, featuring {inst_en} "
            f"and {vocal_en}. The lyrics tell a story about {theme_en}. "
            f"An immersive musical atmosphere with {prod_en}. "
            "Write expressive, original lyrics with a clear verse and chorus structure."
        ),
    }
