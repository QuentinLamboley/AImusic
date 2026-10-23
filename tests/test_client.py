"""Tests sans appels réseau et sans clé API."""
import base64
import unittest
from unittest.mock import patch, Mock

from ace_client import ACEError, build_payload, parse_response, generate_music, extract_lyrics
from text_tools import structure_lyrics


class TestPayload(unittest.TestCase):
    def test_simple(self):
        data = build_payload(mode="simple", prompt="A bright jazz track", duration=80)
        self.assertTrue(data["sample_mode"])
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
        request.return_value = Mock(status_code=200)
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
        request.return_value = Mock(status_code=401)
        with self.assertRaises(ACEError) as ctx:
            generate_music("VERY_PRIVATE_TOKEN", build_payload(mode="simple", prompt="piano"))
        self.assertNotIn("VERY_PRIVATE_TOKEN", str(ctx.exception))

    def test_lyrics_structure(self):
        lyrics = structure_lyrics("First line\nSecond line\n\nHere we sing")
        self.assertIn("[Verse 1]", lyrics)
        self.assertIn("[Chorus]", lyrics)


if __name__ == "__main__":
    unittest.main()
