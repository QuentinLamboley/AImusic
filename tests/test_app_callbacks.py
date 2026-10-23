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

    def test_translation_services_down_does_not_block_song_request(self):
        app = AppTest.from_file(str(APP_FILE)).run(timeout=40)
        app.text_input(key="ace_api_key").set_value("TEST_KEY").run(timeout=40)
        app.text_area(key="simple_description").set_value(
            "Une chanson country joyeuse avec une guitare et une voix grave"
        ).run(timeout=40)
        audio = base64.b64encode(b"TEST-MP3").decode()
        response = Mock(status_code=200, headers={"content-type": "application/json"})
        response.json.return_value = {
            "choices": [{"message": {
                "audio": [{"audio_url": {"url": "data:audio/mpeg;base64," + audio}}]
            }}]
        }
        with (
            patch("text_tools.GoogleTranslator", side_effect=RuntimeError("offline")),
            patch("text_tools.MyMemoryTranslator", side_effect=RuntimeError("offline")),
            patch("ace_client.requests.post", return_value=response) as request,
        ):
            app = click_by_label(app, "✦ Créer ma musique")
        self.assertFalse(app.exception)
        self.assertEqual(request.call_count, 1)
        sent = request.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertIn("Interpret this French musical direction", sent)
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
            patch("text_tools.GoogleTranslator", side_effect=AssertionError("no translation")),
            patch("text_tools.MyMemoryTranslator", side_effect=AssertionError("no translation")),
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
