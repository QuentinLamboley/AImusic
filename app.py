"""MÉLODIA — Studio de création musicale en français (Streamlit + ACE Music)."""
from __future__ import annotations

import html
import json
import re
from datetime import datetime
from typing import Any

import streamlit as st

from ace_client import ACEError, MusicResult, build_payload, generate_music
from text_tools import EXAMPLES, draft_lyrics, structure_lyrics, translate_to_english

st.set_page_config(
    page_title="MÉLODIA • Studio musical IA",
    page_icon="🎼",
    layout="wide",
    initial_sidebar_state="expanded",
)

STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp {font-family:'DM Sans',sans-serif;}
.stApp {background: radial-gradient(ellipse at 72% -7%, rgba(104,83,191,.23),transparent 31%),
radial-gradient(ellipse at 10% 60%,rgba(35,75,111,.13),transparent 36%), #090c17;}
section[data-testid="stSidebar"] {background:#101425;border-right:1px solid rgba(255,255,255,.075);}
.block-container {max-width:1250px;padding-top:2rem;padding-bottom:4rem;}
h1,h2,h3,h4 {font-family:'Outfit',sans-serif;letter-spacing:-.035em;}
h1 {font-weight:800;}
div[data-testid="stTabs"] button[data-baseweb="tab"] {font-size:1rem;font-weight:650;padding:14px 20px;}
div[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:8px;border-bottom:1px solid #303449;}
div.stButton>button[kind="primary"],div.stDownloadButton>button[kind="primary"] {
border:0; background:linear-gradient(110deg,#967bfb 0%,#6054c6 100%);color:white;
font-weight:750;min-height:46px;border-radius:12px;box-shadow:0 8px 25px rgba(110,88,211,.20);}
div.stButton>button[kind="primary"]:hover {background:linear-gradient(110deg,#ac98ff,#7567df);color:white;}
div.stButton>button[kind="secondary"] {border-radius:12px;min-height:40px;border-color:#323a55;background:#171c2e;}
textarea,input {border-radius:12px!important;}
[data-testid="stFileUploader"] {border-radius:14px;}
.hero-wrap {position:relative;border:1px solid #31334c;border-radius:24px;
background:linear-gradient(120deg,rgba(109,91,188,.26),rgba(33,35,61,.73) 54%,rgba(30,62,76,.32));
padding:30px 35px;margin:2px 0 20px;overflow:hidden;}
.hero-wrap:after {content:'♫';font-family:serif;font-size:220px;position:absolute;right:2%;top:-89px;color:rgba(180,160,255,.09);pointer-events:none;}
.eyebrow {font-size:11px;letter-spacing:.17em;color:#c0b7ff;font-weight:800;text-transform:uppercase;}
.hero-title {font-family:'Outfit';font-weight:800;font-size:clamp(36px,4.1vw,58px);letter-spacing:-.05em;line-height:1.08;color:#fff;margin:11px 0;}
.hero-desc {font-size:16px;line-height:1.6;color:#c8cde4;max-width:700px;}
.glass-card {background:linear-gradient(155deg,rgba(25,30,51,.92),rgba(17,21,37,.94));
border:1px solid #2b314b;border-radius:17px;padding:22px 24px;margin:10px 0 18px;}
.glass-card b {color:#f2efff;}
.mini-label {font-size:11px;letter-spacing:.13em;font-weight:850;color:#c5bafb;text-transform:uppercase;}
.muted {color:#a2acc5;font-size:13px;}
.pill {display:inline-block;color:#c6befc;background:rgba(126,103,236,.14);
border:1px solid rgba(162,138,240,.25);border-radius:30px;padding:5px 11px;font-size:12px;font-weight:700;}
.step-num {border-radius:11px;background:#262341;color:#c4b4ff;padding:7px 11px;font-size:15px;font-weight:800;margin-right:8px;}
hr {border-color:#28304a;}
div[data-testid="stAlert"] {border-radius:13px;}
</style>
"""
st.markdown(STYLES, unsafe_allow_html=True)

# Valeurs résidant uniquement dans la session Streamlit ; jamais enregistrées.
DEFAULTS: dict[str, Any] = {
    "music_prompt": "",
    "simple_description": "",
    "song_lyrics": "",
    "song_title": "",
    "song_mode": "Simple",
    "writer_brief": "",
    "writer_mood": "Nostalgique",
    "draft_preview": "",
    "tracks": [],
    "notice": "",
}
for name, default in DEFAULTS.items():
    if name not in st.session_state:
        st.session_state[name] = default

# Les écritures différées sont appliquées AVANT la création des widgets Streamlit.
if "pending_fields" in st.session_state:
    for name, value in st.session_state.pop("pending_fields").items():
        st.session_state[name] = value


def queue_fields(**fields: str) -> None:
    st.session_state["pending_fields"] = fields
    st.rerun()


def flash(message: str) -> None:
    st.session_state["notice"] = message


def insert_example() -> None:
    st.session_state["music_prompt"] = EXAMPLES["prompt"]
    st.session_state["song_lyrics"] = EXAMPLES["lyrics"]
    st.session_state["song_mode"] = "Personnalisé"
    st.session_state["song_title"] = "Ghosts in the Machine"


def append_tag(tag: str) -> None:
    existing = st.session_state.get("song_lyrics", "").rstrip()
    st.session_state["song_lyrics"] = (existing + "\n\n" if existing else "") + f"[{tag}]\n"


def translate_custom_lyrics() -> None:
    try:
        translated, changed = translate_to_english(
            st.session_state.get("song_lyrics", ""), force=True, preserve_sections=True
        )
        if changed:
            st.session_state["song_lyrics"] = translated
            flash("Paroles traduites en anglais. Vérifie-les avant de lancer la création.")
    except Exception:
        flash("Traduction indisponible pour le moment. Vérifie la connexion et réessaie.")


def add_track(result: MusicResult, *, title: str, original: str, sent: str, source_mode: str) -> None:
    record = {
        "title": title.strip() or f"Composition du {datetime.now().strftime('%d/%m à %H:%M')}",
        "created": datetime.now().strftime("%d/%m/%Y · %H:%M"),
        "audio": result.audio,
        "format": result.audio_format,
        "mime": result.mime,
        "original_prompt": original,
        "english_prompt": sent,
        "mode": source_mode,
        "lyrics": result.lyrics,
        "details": result.description,
        "model": result.model,
    }
    st.session_state["tracks"].insert(0, record)
    # Limite mémoire des fichiers audio sur le serveur partagé.
    st.session_state["tracks"] = st.session_state["tracks"][:6]


def file_stub(title: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", title.strip().lower()).strip("-")
    return cleaned[:55] or "ma-composition"


def render_song(track: dict[str, Any], index: int) -> None:
    title = html.escape(track["title"])
    st.markdown(
        f'<div class="glass-card"><span class="mini-label">PISTE {index + 1:02d}</span>'
        f'<h3 style="margin:7px 0 4px">{title}</h3>'
        f'<div class="muted">{html.escape(track["created"])} · {html.escape(track["format"].upper())} · {html.escape(track["mode"])}</div></div>',
        unsafe_allow_html=True,
    )
    st.audio(track["audio"], format=track["mime"])
    c1, c2, c3 = st.columns([1.1, 1.1, 1])
    c1.download_button(
        f"⬇ Télécharger {track['format'].upper()}",
        data=track["audio"],
        file_name=f"{file_stub(track['title'])}.{track['format']}",
        mime=track["mime"],
        use_container_width=True,
        key=f"audio_{index}",
    )
    c2.download_button(
        "📄 Paroles et description",
        data=(
            f"{track['title']}\n\nDESCRIPTION ENVOYÉE À ACE MUSIC\n"
            f"{track['english_prompt']}\n\nPAROLES\n{track['lyrics']}\n"
        ).encode("utf-8"),
        file_name=f"{file_stub(track['title'])}-paroles.txt",
        mime="text/plain",
        use_container_width=True,
        key=f"text_{index}",
    )
    project_data = {k: v for k, v in track.items() if k not in ("audio",)}
    c3.download_button(
        "💾 Fiche du projet",
        data=json.dumps(project_data, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"{file_stub(track['title'])}-projet.json",
        mime="application/json",
        use_container_width=True,
        key=f"project_{index}",
    )
    with st.expander("Voir le prompt envoyé et les paroles obtenues"):
        st.markdown("**Description envoyée (anglais)**")
        st.code(track["english_prompt"], language=None)
        if track["lyrics"]:
            st.markdown("**Paroles retournées par ACE Music**")
            st.code(track["lyrics"], language=None)
        else:
            st.caption("Le service n'a pas fourni de paroles distinctes dans ses métadonnées.")


def prepare_english(text: str, do_translate: bool, preserve: bool = False) -> str:
    if not do_translate:
        return text
    try:
        english, _ = translate_to_english(text, preserve_sections=preserve)
        return english
    except Exception as exc:
        raise ValueError(
            "La traduction automatique est indisponible : tu peux la désactiver et saisir "
            "directement ton texte en anglais, ou réessayer plus tard."
        ) from exc


def run_generation(mode: str, title: str, original_prompt: str, custom_lyrics: str = "", **kwargs: Any) -> MusicResult:
    if not st.session_state.get("ace_api_key", "").strip():
        raise ACEError("Ajoute d'abord ta clé API ACE Music dans la barre de gauche.")
    english = prepare_english(original_prompt.strip(), kwargs.pop("translate_prompt", True))
    if not english.strip():
        raise ValueError("Décris d'abord ta musique.")
    lyrics_en = custom_lyrics
    if mode == "custom" and custom_lyrics.strip() and kwargs.pop("translate_lyrics", True):
        lyrics_en = prepare_english(custom_lyrics, True, preserve=True)
    payload = build_payload(mode=mode, prompt=english, lyrics=lyrics_en, **kwargs)
    result = generate_music(st.session_state["ace_api_key"], payload)
    add_track(result, title=title, original=original_prompt, sent=english, source_mode="Simple" if mode == "simple" else "Personnalisé")
    return result


with st.sidebar:
    st.markdown(
        '<div style="font-family:Outfit;font-size:27px;font-weight:800;margin:9px 0 5px">'
        '🎼 <span style="color:#c8baff">MÉLODIA</span></div>'
        '<div class="muted">Votre studio musical IA · édition française</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("#### 🔑 Connexion personnelle")
    st.text_input(
        "Clé API ACE Music",
        type="password",
        key="ace_api_key",
        placeholder="Coller votre clé ici…",
        help="Champ temporaire de session : la clé n'est pas écrite sur GitHub ni enregistrée dans un fichier.",
    )
    if st.session_state.get("ace_api_key", "").strip():
        st.success("Clé renseignée (non vérifiée)", icon="✅")
    else:
        st.info("Ajoutez votre clé pour créer une chanson.", icon="🔑")
    st.link_button("Obtenir ma clé gratuite ↗", "https://acemusic.ai/api-key", use_container_width=True)
    st.caption("Ne communiquez jamais votre clé à quelqu'un. Elle reste dans la mémoire de votre session Streamlit, puis est transmise à ACE Music pour authentifier vos demandes.")
    if st.button("Oublier la clé de cette session", use_container_width=True):
        st.session_state["ace_api_key"] = ""
        st.rerun()
    st.divider()
    st.markdown("#### ✨ Prise en main")
    st.markdown(
        '<p class="muted">1 · Décrivez votre idée en français.<br>'
        '2 · Choisissez Simple ou Personnalisé.<br>'
        '3 · Lancez la création et téléchargez le morceau.</p>',
        unsafe_allow_html=True,
    )
    st.caption("Aucun GPU ni programme supplémentaire nécessaire sur votre ordinateur.")
    st.link_button("Découvrir ACE Music ↗", "https://acemusic.ai/playground/create", use_container_width=True)

st.markdown(
    '<div class="hero-wrap"><div class="eyebrow">LE STUDIO OÙ VOS IDÉES DEVIENNENT MUSIQUE</div>'
    '<div class="hero-title">Imaginez. Composez.<br><span style="color:#b9a5ff">Écoutez.</span></div>'
    '<div class="hero-desc">Décrivez votre morceau en français, personnalisez les paroles ou '
    'laissez l’intelligence artificielle composer pour vous. Aucune installation, juste de la musique.</div>'
    '<div style="margin-top:16px"><span class="pill">✦ Propulsé par ACE Music</span> '
    '<span class="pill">🇫🇷 Interface 100 % française</span></div></div>',
    unsafe_allow_html=True,
)

if st.session_state.get("notice"):
    st.info(st.session_state.pop("notice"))

composer_tab, writer_tab, library_tab, help_tab = st.tabs(
    ["🎹  Composer", "✍️  Atelier de paroles", "🎧  Ma bibliothèque", "❔  Guide"]
)

with composer_tab:
    st.markdown("### Créez votre prochain morceau")
    st.radio(
        "Comment souhaitez-vous composer ?",
        ["Simple", "Personnalisé"],
        key="song_mode",
        horizontal=True,
        help="Simple : tout est généré à partir d'une description. Personnalisé : vous donnez le style et les paroles.",
    )
    if st.session_state["song_mode"] == "Simple":
        st.markdown(
            '<div class="glass-card"><span class="step-num">01</span>'
            '<b>Une idée suffit</b><div class="muted" style="margin-top:10px">'
            'Expliquez en français ce que vous aimeriez entendre : ambiance, voix, instruments, '
            'thème ou époque. ACE Music inventera les paroles et la composition.</div></div>',
            unsafe_allow_html=True,
        )
        st.text_area(
            "Décrivez la musique de vos rêves",
            key="simple_description",
            height=160,
            placeholder="Exemple : Une chanson rock des années 70, joyeuse et entraînante, "
            "avec une voix masculine grave, un solo de guitare électrique et des paroles "
            "sur un voyage en voiture au bord de la mer.",
        )
    else:
        st.markdown(
            '<div class="glass-card"><span class="step-num">01</span>'
            '<b>À vous de diriger l’orchestre</b><div class="muted" style="margin-top:10px">'
            'Séparez bien la description du style musical et les paroles. '
            'Les marqueurs [Intro], [Verse 1], [Chorus] et [Outro] structurent la chanson.</div></div>',
            unsafe_allow_html=True,
        )
        st.button("✦ Charger votre exemple post-punk", on_click=insert_example)
        st.text_area(
            "Description musicale (prompt)",
            key="music_prompt",
            height=140,
            placeholder="Exemple : Un morceau post-punk mélancolique aux guitares anguleuses, "
            "basse motrice, voix masculine grave et synthétiseurs froids.",
            help="Décrivez le style, les instruments, la production et la voix ; pas les paroles.",
        )
        st.markdown("**Paroles structurées**")
        tagcols = st.columns(5)
        for col, tag in zip(tagcols, ["Intro", "Verse 1", "Chorus", "Bridge", "Outro"]):
            with col:
                st.button(f"+ {tag}", on_click=append_tag, args=(tag,), use_container_width=True)
        st.text_area(
            "Paroles de la chanson",
            key="song_lyrics",
            height=300,
            placeholder="[Intro]\n\n[Verse 1]\nPremier vers…\nDeuxième vers…\n\n[Chorus]\nMon refrain…\n\n[Outro]",
            help="Structure recommandée : [Intro], [Verse 1], [Verse 2], [Chorus], [Bridge], [Outro].",
        )
        c_t1, c_t2 = st.columns([1.2, 2])
        c_t1.button("🌐 Traduire les paroles en anglais", on_click=translate_custom_lyrics, use_container_width=True)
        c_t2.caption("Les balises [Verse], [Chorus], etc. sont conservées.")

    st.markdown(
        '<div class="glass-card"><span class="step-num">02</span><b>Réglez la création</b></div>',
        unsafe_allow_html=True,
    )
    st.text_input(
        "Nom de votre création (facultatif)", key="song_title",
        placeholder="Ex. : Une nuit inoubliable",
    )
    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        duration = st.slider("Durée souhaitée", min_value=20, max_value=360, step=10, value=120, format="%d s")
    with c2:
        audio_format = st.selectbox("Format du fichier", ["mp3", "wav", "flac"], index=0)
    with c3:
        instrumental = st.checkbox("Instrumental (sans voix)", value=False)

    with st.expander("⚙️ Paramètres avancés · facultatif"):
        a1, a2, a3 = st.columns(3)
        with a1:
            set_bpm = st.checkbox("Préciser le tempo (BPM)", value=False)
            bpm = st.number_input("Tempo", min_value=45, max_value=220, value=120, step=1, disabled=not set_bpm)
        with a2:
            key_scale = st.selectbox("Tonalité", ["Libre", "C Major", "C Minor", "D Major", "D Minor", "E Major", "E Minor", "F Major", "F Minor", "G Major", "G Minor", "A Major", "A Minor", "B Major", "B Minor"])
        with a3:
            time_signature = st.selectbox("Signature rythmique", ["Libre", "4/4", "3/4", "6/8", "2/4"])
        thinking = st.checkbox("Composition enrichie (modèle de planification)", value=True)
        use_format = st.checkbox("Laisser ACE Music améliorer la présentation du prompt personnalisé", value=False, disabled=st.session_state["song_mode"] == "Simple")
        translate_prompt = st.checkbox("Traduire automatiquement la description française en anglais", value=True)
        translate_lyrics = st.checkbox("Traduire automatiquement les paroles françaises en anglais", value=True, disabled=st.session_state["song_mode"] == "Simple")
        st.caption("La traduction utilise un service externe. Tous les réglages musicaux sont indicatifs : le modèle peut ne pas les suivre exactement.")

    st.markdown('<div class="glass-card"><span class="step-num">03</span><b>Donnez vie à votre chanson</b></div>', unsafe_allow_html=True)
    st.caption("La génération sollicite l'API ACE Music. Une requête peut durer plusieurs minutes ; évitez de cliquer plusieurs fois.")
    if st.button("✦ Créer ma musique", type="primary", use_container_width=True, key="generate_main"):
        current_mode = st.session_state["song_mode"]
        user_prompt = st.session_state["simple_description"] if current_mode == "Simple" else st.session_state["music_prompt"]
        user_lyrics = "" if current_mode == "Simple" else st.session_state["song_lyrics"]
        try:
            with st.spinner("🎵 Votre musique est en cours de composition chez ACE Music…"):
                run_generation(
                    mode="simple" if current_mode == "Simple" else "custom",
                    title=st.session_state["song_title"],
                    original_prompt=user_prompt,
                    custom_lyrics=user_lyrics,
                    duration=duration,
                    bpm=int(bpm) if set_bpm else None,
                    key_scale="" if key_scale == "Libre" else key_scale,
                    time_signature="" if time_signature == "Libre" else time_signature,
                    audio_format=audio_format,
                    instrumental=instrumental,
                    thinking=thinking,
                    use_format=use_format and current_mode == "Personnalisé",
                    translate_prompt=translate_prompt,
                    translate_lyrics=translate_lyrics and current_mode == "Personnalisé",
                )
            st.success("Votre musique est prête ! Écoutez-la puis téléchargez-la ci-dessous.", icon="🎶")
        except (ACEError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("Une erreur inattendue est survenue. Aucune clé API n'a été affichée. Réessayez ultérieurement.")

    if st.session_state["tracks"]:
        st.markdown("### 🎧 Votre dernière création")
        render_song(st.session_state["tracks"][0], 0)

with writer_tab:
    st.markdown("### ✍️ Donnez des mots à vos idées")
    st.write(
        "Vous pouvez préparer un brouillon sans appel musical, puis le retravailler. "
        "Ou demander à ACE Music d'inventer de vraies paroles par IA : cette option génère aussi une courte piste audio."
    )
    st.text_area(
        "De quoi doit parler la chanson ?",
        key="writer_brief",
        height=130,
        placeholder="Exemple : Une chanson sur un père bricoleur passionné de vieilles machines, "
        "ses inventions improbables et les souvenirs d'enfance dans son atelier.",
    )
    w1, w2 = st.columns(2)
    with w1:
        st.selectbox("Ambiance du brouillon", list(["Nostalgique", "Joyeux", "Épique", "Mélancolique"]), key="writer_mood")
        if st.button("📝 Préparer une ébauche sans API", use_container_width=True):
            try:
                st.session_state["draft_preview"] = draft_lyrics(
                    st.session_state["writer_brief"], st.session_state["writer_mood"]
                )
                st.success("Ébauche créée ! Ce sont des phrases modèles à personnaliser, sans IA ni frais.")
            except ValueError as exc:
                st.warning(str(exc))
    with w2:
        st.markdown("**Écriture IA avec ACE Music**")
        st.caption("Cette fonctionnalité demande au modèle de créer paroles ET musique. Elle utilise une génération API ; ce n'est pas une requête texte gratuite séparée.")
        if st.button("✨ Écrire des paroles avec l'IA ACE Music", type="primary", use_container_width=True):
            try:
                description = st.session_state["writer_brief"].strip()
                if not description:
                    raise ValueError("Décris d'abord le thème souhaité.")
                with st.spinner("ACE Music écrit votre chanson et compose une courte démo…"):
                    generated = run_generation(
                        mode="simple",
                        title="Ébauche IA : " + description[:45],
                        original_prompt="Write expressive, complete original song lyrics about: " + description + ". Structure with [Intro], [Verse 1], [Chorus], [Verse 2], [Chorus], [Outro].",
                        duration=60,
                        audio_format="mp3",
                        instrumental=False,
                        thinking=True,
                        translate_prompt=True,
                    )
                if generated.lyrics:
                    st.session_state["draft_preview"] = generated.lyrics
                    st.success("Paroles IA récupérées ! Une démo sonore est aussi disponible dans votre bibliothèque.")
                else:
                    st.warning("La musique a été créée, mais ACE Music n'a pas renvoyé de paroles exploitables séparément. Écoutez la démo dans la bibliothèque.")
            except (ACEError, ValueError) as exc:
                st.error(str(exc))
            except Exception:
                st.error("L'écriture par ACE Music n'est pas disponible actuellement.")

    st.text_area(
        "Brouillon de paroles · modifiable",
        key="draft_preview",
        height=355,
        placeholder="[Verse 1]\n…\n\n[Chorus]\n…",
    )
    q1, q2 = st.columns(2)
    with q1:
        if st.button("🔧 Structurer les paroles", use_container_width=True):
            newdraft = structure_lyrics(st.session_state["draft_preview"])
            queue_fields(draft_preview=newdraft)
    with q2:
        if st.button("🌐 Traduire le brouillon en anglais", use_container_width=True):
            try:
                translated, _ = translate_to_english(
                    st.session_state["draft_preview"], force=True, preserve_sections=True
                )
                queue_fields(draft_preview=translated)
            except Exception:
                st.warning("Traduction indisponible. Tu peux conserver le texte français ou réessayer.")
    if st.button("↗ Utiliser ces paroles en mode Personnalisé", type="primary", use_container_width=True):
        if not st.session_state["draft_preview"].strip():
            st.warning("Le brouillon est vide.")
        else:
            queue_fields(
                song_lyrics=structure_lyrics(st.session_state["draft_preview"]),
                song_mode="Personnalisé",
            )
    st.caption("Après l'importation, ouvrez l'onglet Composer : vos paroles seront prêtes dans le mode Personnalisé.")

with library_tab:
    st.markdown("### 🎧 Mes créations")
    st.caption(
        "Les morceaux restent dans cette session uniquement (six derniers). "
        "Téléchargez-les pour les conserver : ils disparaîtront lorsque la session sera fermée."
    )
    if not st.session_state["tracks"]:
        st.markdown(
            '<div class="glass-card" style="text-align:center;padding:60px 20px">'
            '<div style="font-size:38px">♫</div><h3>Votre bibliothèque est prête</h3>'
            '<div class="muted">Vos futures compositions apparaîtront ici.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        for idx, track in enumerate(st.session_state["tracks"]):
            render_song(track, idx)
            st.divider()

with help_tab:
    st.markdown("### ❔ Comment utiliser MÉLODIA ?")
    st.markdown("**1. Obtenir sa clé.** Créez une clé sur [ACE Music](https://acemusic.ai/api-key), puis collez-la dans le champ privé à gauche. Chaque utilisateur utilise sa propre clé.")
    st.markdown("**2. Mode Simple.** Écrivez votre idée en français. ACE Music se charge du prompt détaillé, des paroles et de la génération audio.")
    st.markdown("**3. Mode Personnalisé.** Décrivez d'un côté les instruments, le style et la voix, et de l'autre les paroles avec les sections attendues.")
    st.code("[Intro]\n\n[Verse 1]\nPremière strophe\nDeuxième ligne\n\n[Chorus]\nUn refrain qui revient\n\n[Outro]\nDerniers mots", language=None)
    st.markdown("**4. Atelier de paroles.** L'ébauche hors ligne propose seulement des phrases modèles. Le bouton d'écriture IA appelle ACE Music, qui génère également une piste.")
    st.markdown("**5. Traduction.** Les textes français peuvent être traduits en anglais automatiquement, et les balises de chanson sont préservées. La traduction s'appuie sur un service tiers.")
    st.markdown("**6. Téléchargement.** Dès qu'un morceau apparaît, utilisez le bouton de téléchargement pour le conserver sur votre ordinateur.")
    st.warning("ACE Music est un service tiers : la disponibilité et les limites d'API sont indépendantes de cette application. Une erreur de délai ne signifie pas toujours que la requête a échoué côté serveur ; évitez les renvois en boucle.")
    st.info("Protection de votre clé : aucun fichier ou dépôt GitHub ne contient la clé. Elle sert uniquement aux requêtes de votre session. N'enregistrez pas de secret dans les champs de description ou de paroles.")
