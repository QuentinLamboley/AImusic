"""Client minimal de l'API ACE Music. Les clés ne sont jamais persistées."""
from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests

BASE_URL = "https://api.acemusic.ai"
MODEL = "acemusic/acestep-v15-turbo"
MIME = {"mp3": "audio/mpeg", "wav": "audio/wav", "flac": "audio/flac", "ogg": "audio/ogg", "aac": "audio/aac", "m4a": "audio/mp4"}
MAX_AUDIO_BYTES = 55 * 1024 * 1024


class ACEError(Exception):
    """Erreur contrôlée, sans informations d'authentification."""


@dataclass
class MusicResult:
    audio: bytes
    audio_format: str
    mime: str
    description: str
    lyrics: str
    model: str


def build_payload(
    *,
    mode: str,
    prompt: str,
    lyrics: str = "",
    duration: int = 120,
    bpm: int | None = None,
    key_scale: str = "",
    time_signature: str = "",
    audio_format: str = "mp3",
    instrumental: bool = False,
    thinking: bool = True,
    use_format: bool = False,
    seed: int | None = None,
) -> dict[str, Any]:
    """Construit les deux formats officiels ACE-Step sans ambiguïté."""
    if mode not in ("simple", "custom"):
        raise ValueError("Mode inconnu.")
    if not prompt.strip():
        raise ValueError("Il faut décrire la musique.")
    if audio_format not in ("mp3", "wav", "flac"):
        raise ValueError("Format audio non pris en charge.")
    if not 10 <= int(duration) <= 600:
        raise ValueError("La durée doit être comprise entre 10 et 600 secondes.")
    cfg: dict[str, Any] = {
        "duration": int(duration),
        "format": audio_format,
        "vocal_language": "en",
        "instrumental": bool(instrumental),
    }
    if bpm is not None:
        cfg["bpm"] = int(bpm)
    if key_scale.strip():
        cfg["key_scale"] = key_scale.strip()
    if time_signature.strip():
        cfg["time_signature"] = time_signature.strip()

    if mode == "simple":
        content = prompt.strip()
    else:
        if not instrumental and not lyrics.strip():
            raise ValueError("Ajoute des paroles structurées ou active le mode instrumental.")
        clean_prompt = prompt.strip().replace("</prompt>", "").replace("<prompt>", "")
        clean_lyrics = "[Instrumental]" if instrumental else lyrics.strip().replace("</lyrics>", "").replace("<lyrics>", "")
        content = f"<prompt>{clean_prompt}</prompt>\n<lyrics>{clean_lyrics}</lyrics>"

    body: dict[str, Any] = {
        "model": MODEL,
        "messages": [{"role": "user", "content": content}],
        "stream": True,
        "sample_mode": mode == "simple",
        "thinking": bool(thinking),
        "use_format": bool(use_format) if mode == "custom" else False,
        "batch_size": 1,
        "audio_config": cfg,
    }
    if seed is not None:
        body["seed"] = int(seed)
    return body


def extract_lyrics(content: str) -> str:
    """Récupère les paroles produites par ACE-Step dans sa réponse texte."""
    if not content:
        return ""
    match = re.search(r"(?im)^#{1,4}\s*(?:lyrics|song lyrics|paroles)\s*:?\s*$", content)
    if match:
        part = content[match.end():]
        part = re.split(r"(?m)^#{1,4}\s+[^\n]+", part, maxsplit=1)[0]
        return part.strip()
    match = re.search(r"(?is)<lyrics>(.*?)</lyrics>", content)
    if match:
        return match.group(1).strip()
    # Ne pas confondre les métadonnées et les paroles.
    if re.search(r"(?i)\[(verse|chorus|intro|outro|bridge|pre-chorus)", content):
        start = re.search(r"(?i)\[(verse|chorus|intro|outro|bridge|pre-chorus)", content)
        if start:
            return content[start.start():].strip()
    return ""


def _coerce_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join((p.get("text", "") if isinstance(p, dict) else str(p)) for p in content)
    return ""


def _decode_b64(value: str) -> tuple[bytes, str]:
    match = re.match(r"^data:(audio/[\w.+-]+);base64,(.+)$", value, re.DOTALL | re.IGNORECASE)
    if match:
        mime, encoded = match.group(1).lower(), match.group(2)
    else:
        mime, encoded = "audio/mpeg", value
    if len(encoded) > MAX_AUDIO_BYTES * 2:
        raise ACEError("Le fichier audio retourné dépasse la taille autorisée.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ACEError("L'audio retourné est incomplet ou invalide.") from exc
    if not raw or len(raw) > MAX_AUDIO_BYTES:
        raise ACEError("Le fichier audio retourné est vide ou trop volumineux.")
    return raw, mime


def _audio_item(item: Any) -> tuple[bytes, str] | None:
    if isinstance(item, str):
        if item.startswith("data:audio/"):
            return _decode_b64(item)
        return None
    if not isinstance(item, dict):
        return None
    url = item.get("audio_url")
    if isinstance(url, dict):
        url = url.get("url")
    for candidate in (url, item.get("data"), item.get("b64_json"), item.get("base64")):
        if isinstance(candidate, str) and candidate:
            if candidate.startswith("data:audio/") or (not candidate.startswith(("http://", "https://"))):
                return _decode_b64(candidate)
            parsed = urlparse(candidate)
            # Ne jamais télécharger vers une adresse arbitraire venant de la réponse.
            if parsed.scheme == "https" and parsed.hostname == "api.acemusic.ai":
                response = requests.get(candidate, timeout=(10, 90), stream=True, allow_redirects=False)
                try:
                    response.raise_for_status()
                    chunks, size = [], 0
                    for chunk in response.iter_content(1024 * 256):
                        size += len(chunk)
                        if size > MAX_AUDIO_BYTES:
                            raise ACEError("Le fichier retourné est trop volumineux.")
                        chunks.append(chunk)
                    return b"".join(chunks), response.headers.get("content-type", "audio/mpeg").split(";")[0]
                finally:
                    response.close()
    return None


def parse_response(data: dict[str, Any], fallback_format: str = "mp3") -> MusicResult:
    choices = data.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        raise ACEError("L'API n'a pas retourné de chanson. Réessaie ultérieurement.")
    message = choices[0].get("message") or {}
    if not isinstance(message, dict):
        raise ACEError("Réponse musicale non reconnue.")
    text_content = _coerce_text(message.get("content"))
    items = message.get("audio") or []
    if isinstance(items, (str, dict)):
        items = [items]
    if not isinstance(items, list):
        items = []
    # Formats courants des passerelles OpenAI compatibles.
    if not items:
        items = [message.get("audio_url"), message.get("audio_data"), message.get("audio_base64")]
    audio = None
    for item in items:
        if item:
            audio = _audio_item(item)
            if audio:
                break
    if not audio:
        raise ACEError("La requête a répondu, mais aucun fichier audio n'a été trouvé. Vérifie l'état du service.")
    binary, mime = audio
    fmt = next((k for k, v in MIME.items() if v == mime), fallback_format)
    return MusicResult(
        audio=binary,
        audio_format=fmt,
        mime=mime,
        description=text_content,
        lyrics=extract_lyrics(text_content),
        model=str(data.get("model") or MODEL),
    )


def parse_stream(lines: Any, fallback_format: str = "mp3", on_progress: Any = None) -> MusicResult:
    """Assemble le flux SSE ACE-Step (métadonnées, battements de coeur, audio).

    Un évènement peut occuper plusieurs lignes 'data:'. Les morceaux audio base64
    ne sont jamais stockés dans les logs. Aucun appel API supplémentaire.
    """
    content_parts: list[str] = []
    audio_items: list[Any] = []
    model_id = MODEL
    saw_event = False
    started_generation = False
    event_lines: list[str] = []

    def emit(message: str) -> None:
        if on_progress is not None:
            try:
                on_progress(message)
            except Exception:
                pass  # Une mise à jour UI ne doit pas gâcher un morceau.

    def handle_event(text: str) -> bool:
        nonlocal model_id, saw_event, started_generation
        if text.strip() == "[DONE]":
            return True
        try:
            chunk = __import__("json").loads(text)
        except (ValueError, TypeError):
            return False
        if not isinstance(chunk, dict):
            return False
        if chunk.get("error"):
            raise ACEError("ACE Music a signalé une erreur pendant la composition. Aucune nouvelle requête n'a été envoyée.")
        saw_event = True
        model_id = str(chunk.get("model") or model_id)
        choices = chunk.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            return False
        choice = choices[0]
        delta = choice.get("delta") or choice.get("message") or {}
        if not isinstance(delta, dict):
            return False
        content = _coerce_text(delta.get("content"))
        # ACE-Step émet "." toutes les deux secondes pour maintenir le flux.
        if content and content != ".":
            content_parts.append(content)
            if not started_generation:
                emit("🎼 Analyse musicale et préparation des paroles…")
                started_generation = True
        if content == "." and not started_generation:
            emit("🎚️ Le serveur compose votre musique…")
            started_generation = True
        audio = delta.get("audio") or []
        if isinstance(audio, (str, dict)):
            audio = [audio]
        if isinstance(audio, list) and audio:
            audio_items.extend(audio)
            emit("🎧 Réception et préparation de votre fichier audio…")
        return choice.get("finish_reason") == "stop"

    try:
        for raw in lines:
            if isinstance(raw, bytes):
                line = raw.decode("utf-8", errors="replace")
            else:
                line = str(raw)
            line = line.rstrip("\r\n")
            if line.startswith("data:"):
                event_lines.append(line[5:].lstrip())
            elif not line and event_lines:
                done = handle_event("\n".join(event_lines))
                event_lines = []
                if done:
                    break
        if event_lines:
            handle_event("\n".join(event_lines))
    except requests.RequestException as exc:
        if not audio_items:
            raise ACEError(
                "La connexion avec ACE Music a été interrompue avant la réception du fichier. "
                "Cela peut venir du serveur distant, même après une seule tentative."
            ) from exc
        # Un fichier audio complet déjà reçu peut encore être récupéré.

    if not audio_items:
        if saw_event:
            raise ACEError(
                "ACE Music a répondu progressivement, mais n'a fourni aucun audio. "
                "La génération a peut-être expiré sur ses serveurs."
            )
        raise ACEError(
            "ACE Music n'a retourné aucun évènement musical. "
            "Le serveur peut être surchargé ou indisponible."
        )
    result = parse_response(
        {"model": model_id, "choices": [{"message": {
            "content": "".join(content_parts),
            "audio": audio_items,
        }}]},
        fallback_format=fallback_format,
    )
    emit("✅ Le morceau est prêt.")
    return result


def generate_music(
    api_key: str,
    payload: dict[str, Any],
    on_progress: Any = None,
) -> MusicResult:
    """Un seul POST SSE ; ni relance automatique ni clé dans les messages d'erreur."""
    if not api_key.strip():
        raise ACEError("Renseigne ta clé API ACE Music dans le panneau de gauche.")
    request_payload = dict(payload)
    # Le streaming fournit des évènements réguliers, contrairement à une unique
    # réponse bloquante, et peut éviter certains délais d'attente réseau.
    request_payload["stream"] = True
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json=request_payload,
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream, application/json",
            },
            timeout=(20, 150),  # Délai entre deux données, PAS durée totale.
            stream=True,
            allow_redirects=False,
        )
    except requests.Timeout as exc:
        raise ACEError(
            "ACE Music n'a pas répondu à temps. Il s'agit d'une expiration de connexion, "
            "pas nécessairement d'un quota ou d'une erreur de saisie."
        ) from exc
    except requests.RequestException as exc:
        raise ACEError("Impossible de joindre ACE Music. Vérifie ta connexion ou l'état du fournisseur.") from exc

    try:
        if response.status_code in (401, 403):
            raise ACEError("Clé API refusée. Vérifie-la sur acemusic.ai/api-key.")
        if response.status_code == 429:
            raise ACEError("ACE Music limite actuellement les requêtes (HTTP 429). Réessaie plus tard.")
        if response.status_code == 504:
            raise ACEError(
                "ACE Music a dépassé son temps de réponse (HTTP 504), même avec une seule tentative. "
                "Un incident du service externe a déjà été signalé. Aucun nouvel appel n'a été lancé."
            )
        if response.status_code in (502, 503):
            raise ACEError(
                f"ACE Music ne peut pas traiter la requête actuellement (HTTP {response.status_code}). "
                "Aucun nouvel appel n'a été lancé."
            )
        if response.status_code >= 400:
            raise ACEError(f"ACE Music a refusé la génération (HTTP {response.status_code}).")
        if response.status_code in (301, 302, 303, 307, 308):
            raise ACEError("ACE Music redirige sa requête au lieu de générer un morceau.")

        content_type = (response.headers or {}).get("content-type", "").lower()
        fallback_format = request_payload.get("audio_config", {}).get("format", "mp3")
        if "text/event-stream" in content_type:
            return parse_stream(response.iter_lines(), fallback_format, on_progress)

        # Compatibilité avec un serveur qui ignore 'stream: true'.
        try:
            data = response.json()
        except ValueError as exc:
            raise ACEError("ACE Music a renvoyé une réponse inattendue, non musicale.") from exc
        if not isinstance(data, dict):
            raise ACEError("Réponse ACE Music incorrecte.")
        return parse_response(data, fallback_format)
    finally:
        response.close()
