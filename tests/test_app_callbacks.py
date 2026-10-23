"""Tests fonctionnels des deux boutons de l'atelier, sans appel au réseau."""
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import base64

from streamlit.testing.v1 import AppTest
from random_music import make_random_idea

APP_FILE = Path(__file__).resolve().parent.parent / "app.py"


def click_by_label(app: AppTest, label: str) -> AppTest:
    button = next((b for b in app.button if b.label == label), None)
    if button is None:
        raise AssertionError(f"Bouton manquant : {label}")
    return button.click().run(timeout=40)


class WriterButtonsTest(unittest.TestCase):
    def test_structure_updates_the_visible_editor(self):
        app = AppTest.from_file(str(APP_FILE)).run(timeout=40)
        self.assertFalse(app.exception)
        app.text_area(key="draft_preview").set_value(
            "Le vent souffle dans la vallée\nJe prends la route\n\nJe pars demain"
        ).run(timeout=40)
        app = click_by_label(app, "🔧 Structurer les paroles")
        self.assertFalse(app.exception)
        self.assertIn("[Verse 1]", app.session_state["draft_preview"])
        self.assertIn("[Chorus]", app.session_state["draft_preview"])

    def test_transfer_selects_composer_and_sets_custom_lyrics(self):
        app = AppTest.from_file(str(APP_FILE)).run(timeout=40)
        self.assertFalse(app.exception)
        app.text_area(key="draft_preview").set_value("Une chanson pour mon père").run(timeout=40)
        app = click_by_label(app, "↗ Utiliser ces paroles en mode Personnalisé")
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["song_mode"], "Personnalisé")
        self.assertEqual(app.session_state["melodia_active_tab"], "🎹  Composer")
        self.assertIn("Une chanson pour mon père", app.session_state["song_lyrics"])

    def test_french_custom_lyrics_reach_api_unchanged(self):
        app = AppTest.from_file(str(APP_FILE)).run(timeout=40)
        app.text_input(key="ace_api_key").set_value("TEST_KEY").run(timeout=40)
        app.radio(key="song_mode").set_value("Personnalisé").run(timeout=40)
        app.selectbox(key="lyrics_language").set_value("Français").run(timeout=40)
        prompt = "Une chanson country avec guitare acoustique"
        original_lyrics = "[Verse 1]\\nLa lumière danse sur ma maison\\n\\n[Chorus]\\nJe me souviens"
        app.text_area(key="music_prompt").set_value(prompt).run(timeout=40)
        app.text_area(key="song_lyrics").set_value(original_lyrics).run(timeout=40)

        music_response = Mock(status_code=200, headers={"content-type": "application/json"})
        encoded = base64.b64encode(b"TEST-MP3").decode()
        music_response.json.return_value = {
            "choices": [{"message": {
                "audio": [{"audio_url": {"url": "data:audio/mpeg;base64," + encoded}}]
            }}]
        }
        translator_response = Mock(status_code=200)
        translator_response.json.return_value = [[[
            "A warm country song featuring acoustic guitar", ""
        ]]]
        with (
            patch("text_tools.requests.get", return_value=translator_response) as translate,
            patch("ace_client.requests.post", return_value=music_response) as api,
        ):
            app = click_by_label(app, "✦ Créer ma musique")
        self.assertFalse(app.exception)
        self.assertEqual(api.call_count, 1)
        self.assertEqual(translate.call_count, 1)
        sent = api.call_args.kwargs["json"]
        self.assertEqual(sent["audio_config"]["vocal_language"], "fr")
        self.assertEqual(sent["vocal_language"], "fr")
        self.assertIn("<prompt>A warm country song featuring acoustic guitar</prompt>", sent["messages"][0]["content"])
        self.assertIn("<lyrics>" + original_lyrics + "</lyrics>", sent["messages"][0]["content"])

    def test_french_simple_mode_requests_french_vocals(self):
        app = AppTest.from_file(str(APP_FILE)).run(timeout=40)
        app.text_input(key="ace_api_key").set_value("TEST_KEY").run(timeout=40)
        app.selectbox(key="lyrics_language").set_value("Français").run(timeout=40)
        app.text_area(key="simple_description").set_value(
            "Une chanson joyeuse avec un violon"
        ).run(timeout=40)
        music_response = Mock(status_code=200, headers={"content-type": "application/json"})
        encoded = base64.b64encode(b"TEST-MP3").decode()
        music_response.json.return_value = {
            "choices": [{"message": {
                "audio": [{"audio_url": {"url": "data:audio/mpeg;base64," + encoded}}]
            }}]
        }
        translator_response = Mock(status_code=200)
        translator_response.json.return_value = [[["A joyful song with violin", ""]]]
        with (
            patch("text_tools.requests.get", return_value=translator_response),
            patch("ace_client.requests.post", return_value=music_response) as api,
        ):
            app = click_by_label(app, "✦ Créer ma musique")
        self.assertFalse(app.exception)
        content = api.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertIn("in French", content)
        self.assertEqual(api.call_args.kwargs["json"]["audio_config"]["vocal_language"], "fr")

    def test_random_mode_creates_and_refreshes_idea(self):
        idea = make_random_idea()
        self.assertTrue(idea["fr"])
        self.assertTrue(idea["en"])
        self.assertNotEqual(idea["fr"], idea["en"])
        app = AppTest.from_file(str(APP_FILE)).run(timeout=40)
        app.radio(key="song_mode").set_value("Aléatoire").run(timeout=40)
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state["random_idea"]["en"].startswith("An original"))
        app = click_by_label(app, "🎲 Une autre inspiration")
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state["random_idea"]["fr"])

    def test_translation_services_down_prevents_french_api_request(self):
        import requests
        app = AppTest.from_file(str(APP_FILE)).run(timeout=40)
        app.text_input(key="ace_api_key").set_value("TEST_KEY").run(timeout=40)
        app.text_area(key="simple_description").set_value(
            "Une chanson country joyeuse avec une guitare et une voix grave"
        ).run(timeout=40)
        with (
            patch("text_tools.requests.get", side_effect=requests.Timeout("offline")),
            patch("ace_client.requests.post") as api,
        ):
            app = click_by_label(app, "✦ Créer ma musique")
        self.assertFalse(app.exception)
        api.assert_not_called()
        self.assertEqual(len(app.session_state["tracks"]), 0)
        self.assertGreater(len(app.error), 0)

    def test_french_song_sends_only_english_to_api(self):
        app = AppTest.from_file(str(APP_FILE)).run(timeout=40)
        app.text_input(key="ace_api_key").set_value("TEST_KEY").run(timeout=40)
        app.text_area(key="simple_description").set_value(
            "Une chanson country joyeuse avec guitare"
        ).run(timeout=40)
        response = Mock(status_code=200, headers={"content-type": "application/json"})
        audio = base64.b64encode(b"TEST-MP3").decode()
        response.json.return_value = {
            "choices": [{"message": {
                "audio": [{"audio_url": {"url": "data:audio/mpeg;base64," + audio}}]
            }}]
        }
        translation_response = Mock(status_code=200)
        translation_response.json.return_value = [[[
            "A cheerful country song with acoustic guitar", ""
        ]]]
        with (
            patch("text_tools.requests.get", return_value=translation_response),
            patch("ace_client.requests.post", return_value=response) as api,
        ):
            app = click_by_label(app, "✦ Créer ma musique")
        self.assertFalse(app.exception)
        self.assertEqual(api.call_count, 1)
        sent = api.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertTrue(sent.startswith("A cheerful country song with acoustic guitar"))
        self.assertIn("lyrics in French", sent)
        self.assertEqual(len(app.session_state["tracks"]), 1)

    def test_random_generation_works_without_translation_services(self):
        app = AppTest.from_file(str(APP_FILE)).run(timeout=40)
        app.text_input(key="ace_api_key").set_value("TEST_KEY").run(timeout=40)
        app.radio(key="song_mode").set_value("Aléatoire").run(timeout=40)
        audio = base64.b64encode(b"TEST-MP3").decode()
        response = Mock(status_code=200, headers={"content-type": "application/json"})
        response.json.return_value = {
            "choices": [{"message": {
                "audio": [{"audio_url": {"url": "data:audio/mpeg;base64," + audio}}]
            }}]
        }
        with (
            patch("text_tools.requests.get", side_effect=AssertionError("No translator needed")),
            patch("ace_client.requests.post", return_value=response) as request,
        ):
            app = click_by_label(app, "✦ Créer ma musique")
        self.assertFalse(app.exception)
        self.assertEqual(request.call_count, 1)
        sent = request.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertTrue(sent.startswith("An original"))
        self.assertEqual(app.session_state["tracks"][0]["mode"], "Aléatoire")


if __name__ == "__main__":
    unittest.main()
