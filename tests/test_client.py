"""Tests sans appels réseau et sans clé API."""
import base64
import unittest
from unittest.mock import patch, Mock

from ace_client import ACEError, build_payload, parse_response, generate_music, extract_lyrics, parse_stream, MAX_GENERATION_SECONDS
from text_tools import structure_lyrics, translate_to_english, TranslationUnavailable


class TestPayload(unittest.TestCase):
    def test_simple(self):
        data = build_payload(mode="simple", prompt="A bright jazz track", duration=80, vocal_language="en")
        self.assertTrue(data["sample_mode"])
        self.assertTrue(data["stream"])
        self.assertFalse(data["use_cot_caption"])
        self.assertFalse(data["use_cot_language"])
        self.assertFalse(data["use_cot_metas"])
        self.assertEqual(data["messages"][0]["content"], "A bright jazz track")
        self.assertEqual(data["audio_config"]["duration"], 80)
        self.assertEqual(data["audio_config"]["vocal_language"], "en")
        self.assertEqual(data["model"], "acemusic/acestep-v15-turbo")

    def test_custom_structured_lyrics(self):
        lyrics = "[Intro]\n\n[Verse 1]\nHello world\n\n[Chorus]\nAll together"
        data = build_payload(mode="custom", prompt="Dreamy guitars", lyrics=lyrics, duration=90, bpm=115)
        content = data["messages"][0]["content"]
        self.assertIn("<prompt>Dreamy guitars</prompt>", content)
        self.assertIn("<lyrics>" + lyrics + "</lyrics>", content)
        self.assertFalse(data["sample_mode"])
        self.assertEqual(data["audio_config"]["bpm"], 115)

    def test_default_language_is_french(self):
        data = build_payload(mode="simple", prompt="A folk song in French")
        self.assertEqual(data["audio_config"]["vocal_language"], "fr")
        self.assertEqual(data["vocal_language"], "fr")

    def test_custom_french_lyrics_are_sent_unchanged(self):
        lyrics = "[Intro]\\n\\n[Verse 1]\\nLe vent souffle sur nos montagnes\\n\\n[Chorus]\\nJe reviens vers toi"
        data = build_payload(
            mode="custom", prompt="A warm country ballad",
            lyrics=lyrics, vocal_language="fr",
        )
        self.assertEqual(data["vocal_language"], "fr")
        self.assertEqual(data["audio_config"]["vocal_language"], "fr")
        self.assertIn("<lyrics>" + lyrics + "</lyrics>", data["messages"][0]["content"])
        self.assertNotIn("Write and sing the lyrics in English", data["messages"][0]["content"])

    def test_selectable_language_codes(self):
        for code in ("fr", "en", "es", "de", "it", "pt"):
            with self.subTest(code=code):
                data = build_payload(
                    mode="simple", prompt="Acoustic guitar track", vocal_language=code,
                )
                self.assertEqual(data["audio_config"]["vocal_language"], code)
        with self.assertRaises(ValueError):
            build_payload(mode="simple", prompt="Music", vocal_language="invalid")

    def test_instrumental_without_lyrics(self):
        data = build_payload(mode="custom", prompt="Epic orchestra", lyrics="", instrumental=True)
        self.assertIn("[Instrumental]", data["messages"][0]["content"])

    def test_custom_needs_lyrics_if_vocal(self):
        with self.assertRaises(ValueError):
            build_payload(mode="custom", prompt="Jazz", lyrics="", instrumental=False)

    def test_duration_limit(self):
        with self.assertRaises(ValueError):
            build_payload(mode="simple", prompt="Jazz", duration=999)

    def test_audio_response_and_lyrics(self):
        b64 = base64.b64encode(b"FAKE-MP3").decode()
        result = parse_response({
            "choices": [{"message": {
                "content": "## Metadata\nBPM: 100\n\n## Lyrics\n[Verse 1]\nHello\n[Chorus]\nWorld",
                "audio": [{"type": "audio_url", "audio_url": {"url": f"data:audio/mpeg;base64,{b64}"}}]
            }}]
        })
        self.assertEqual(result.audio, b"FAKE-MP3")
        self.assertEqual(result.audio_format, "mp3")
        self.assertIn("[Chorus]", result.lyrics)
        self.assertNotIn("BPM:", result.lyrics)

    def test_no_audio(self):
        with self.assertRaises(ACEError):
            parse_response({"choices": [{"message": {"content": "Processing"}}]})

    def test_bad_audio(self):
        with self.assertRaises(ACEError):
            parse_response({"choices": [{"message": {"audio": [{"audio_url": {"url": "data:audio/mpeg;base64,garbage!!"}}]}}]})

    @patch("ace_client.requests.post")
    def test_api_key_only_in_header(self, request):
        b64 = base64.b64encode(b"AUDIO").decode()
        request.return_value = Mock(status_code=200, headers={"content-type": "application/json"})
        request.return_value.json.return_value = {
            "choices": [{"message": {"audio": [{"audio_url": {"url": f"data:audio/mpeg;base64,{b64}"}}]}}]
        }
        payload = build_payload(mode="simple", prompt="piano")
        result = generate_music("SECRET_TEST", payload)
        self.assertEqual(result.audio, b"AUDIO")
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer SECRET_TEST")
        self.assertNotIn("SECRET_TEST", str(request.call_args.kwargs["json"]))

    @patch("ace_client.requests.post")
    def test_api_error_does_not_print_key(self, request):
        request.return_value = Mock(status_code=401, headers={})
        with self.assertRaises(ACEError) as ctx:
            generate_music("VERY_PRIVATE_TOKEN", build_payload(mode="simple", prompt="piano"))
        self.assertNotIn("VERY_PRIVATE_TOKEN", str(ctx.exception))

    def test_lyrics_structure(self):
        lyrics = structure_lyrics("First line\nSecond line\n\nHere we sing")
        self.assertIn("[Verse 1]", lyrics)
        self.assertIn("[Chorus]", lyrics)

    @patch("text_tools.requests.get")
    def test_google_translation_returns_english(self, get):
        response = Mock(status_code=200)
        response.json.return_value = [[["A father repairing vintage machines", ""]]]
        get.return_value = response
        translated, done = translate_to_english("Un père qui bricole des machines anciennes")
        self.assertTrue(done)
        self.assertIn("father", translated.lower())
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.kwargs["params"]["tl"], "en")
        self.assertIn("timeout", get.call_args.kwargs)

    @patch("text_tools.requests.get")
    def test_translation_uses_secondary_provider_when_google_fails(self, get):
        import requests
        response = Mock(status_code=200)
        response.json.return_value = {
            "responseStatus": 200,
            "responseData": {"translatedText": "A father repairing vintage machines"},
        }
        get.side_effect = [requests.Timeout("offline"), response]
        translated, done = translate_to_english("Un père qui bricole des machines anciennes")
        self.assertTrue(done)
        self.assertIn("father", translated.lower())
        self.assertEqual(get.call_count, 2)
        self.assertIn("mymemory", get.call_args.args[0])

    @patch("text_tools.requests.get")
    def test_both_translators_down_fails_without_sending_french(self, get):
        import requests
        get.side_effect = requests.Timeout("offline")
        with self.assertRaises(TranslationUnavailable):
            translate_to_english("Une chanson douce avec guitare et voix grave")
        self.assertEqual(get.call_count, 2)

    @patch("text_tools.requests.get")
    def test_verses_preserved_in_english(self, get):
        response = Mock(status_code=200)
        response.json.return_value = [[["I dream of leaving\nI see the light\nI sing", ""]]]
        get.return_value = response
        source = "[Verse 1]\nJe rêve de partir\nJe vois la lumière\n\n[Chorus]\nJe chante"
        translated, done = translate_to_english(source, preserve_sections=True)
        self.assertTrue(done)
        self.assertIn("[Verse 1]", translated)
        self.assertIn("[Chorus]", translated)
        self.assertIn("I dream of leaving", translated)
        self.assertNotIn("Je rêve", translated)

    def test_already_english_needs_no_network(self):
        with patch("text_tools.requests.get") as get:
            translated, changed = translate_to_english(
                "A bright indie rock song featuring jangly guitars and warm vocal harmonies."
            )
        self.assertFalse(changed)
        self.assertIn("guitars", translated)
        get.assert_not_called()

    def test_stream_deadline_stops_heartbeat_loop(self):
        from ace_client import ACEError
        with self.assertRaises(ACEError) as raised:
            parse_stream(["data: [DONE]", ""], deadline_at=0)
        self.assertIn("4 minutes", str(raised.exception))

    def test_sse_heartbeat_and_audio(self):
        """Assemblage des fragments SSE + battements de coeur sans appel réseau."""
        b64 = base64.b64encode(b"AUDIO-STREAM").decode()
        events = [
            b'data: {"model":"acemusic/acestep-v15-turbo","choices":[{"delta":{"content":"## Lyrics\n"}}]}',
            b'',
            'data: {"choices":[{"delta":{"content":"."}}]}',
            '',
            'data: {"choices":[{"delta":{"content":"[Verse 1] Hello"}}]}',
            '',
            'data: {"choices":[{"delta":{"audio":[{"type":"audio_url","audio_url":{"url":"data:audio/mpeg;base64,' + b64 + '"}}]},"finish_reason":"stop"}]}',
            '',
            'data: [DONE]',
            '',
        ]
        # La première ligne ci-dessus contient une valeur JSON avec saut de ligne
        # littéral ; on la remplace par un fragment JSON réel valide.
        events[0] = b'data: {"choices":[{"delta":{"content":"## Lyrics\\n"}}]}'
        reports = []
        result = parse_stream(events, "mp3", reports.append)
        self.assertEqual(result.audio, b"AUDIO-STREAM")
        self.assertEqual(result.audio_format, "mp3")
        self.assertIn("[Verse 1] Hello", result.lyrics)
        self.assertNotIn("..", result.description)
        self.assertTrue(reports)

    def test_streaming_stops_on_first_audio(self):
        b64 = base64.b64encode(b"SINGLE-CALL").decode()
        response = Mock(status_code=200, headers={"content-type": "text/event-stream"})
        response.iter_lines.return_value = [
            f'data: {{"choices":[{{"delta":{{"audio":[{{"audio_url":{{"url":"data:audio/mpeg;base64,{b64}"}}}}]}},"finish_reason":"stop"}}]}}',
            '',
            'data: [DONE]',
        ]
        with patch("ace_client.requests.post", return_value=response) as request:
            result = generate_music("ONLY_PRIVATE_HEADER", build_payload(mode="simple", prompt="piano"))
        self.assertEqual(result.audio, b"SINGLE-CALL")
        self.assertEqual(request.call_count, 1)
        self.assertTrue(request.call_args.kwargs["stream"])
        self.assertTrue(request.call_args.kwargs["json"]["stream"])
        self.assertNotIn("ONLY_PRIVATE_HEADER", str(request.call_args.kwargs["json"]))
        response.close.assert_called_once()

    def test_single_504_does_not_trigger_retries(self):
        response = Mock(status_code=504, headers={"content-type": "text/html"})
        with patch("ace_client.requests.post", return_value=response) as request:
            with self.assertRaises(ACEError) as caught:
                generate_music("SECRET_TEST", build_payload(mode="simple", prompt="piano"))
        self.assertIn("une seule tentative", str(caught.exception))
        self.assertEqual(request.call_count, 1)
        response.close.assert_called_once()

    def test_sse_missing_audio(self):
        with self.assertRaises(ACEError):
            parse_stream(['data: {"choices":[{"delta":{"content":"."}}]}', "", "data: [DONE]", ""])

    def test_sse_multiline_event(self):
        b64 = base64.b64encode(b"WAV-DATA").decode()
        result = parse_stream([
            'data: {"choices":',
            f'data: [{{"delta":{{"audio":[{{"audio_url":{{"url":"data:audio/wav;base64,{b64}"}}}}]}}}}]}}',
            "",
            "data: [DONE]", "",
        ], "wav")
        self.assertEqual(result.audio, b"WAV-DATA")
        self.assertEqual(result.audio_format, "wav")


if __name__ == "__main__":
    unittest.main()
