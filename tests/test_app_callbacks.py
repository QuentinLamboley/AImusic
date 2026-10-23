"""Tests fonctionnels des deux boutons de l'atelier, sans appel au réseau."""
import unittest

from streamlit.testing.v1 import AppTest


def click_by_label(app: AppTest, label: str) -> AppTest:
    button = next((b for b in app.button if b.label == label), None)
    if button is None:
        raise AssertionError(f"Bouton manquant : {label}")
    return button.click().run(timeout=40)


class WriterButtonsTest(unittest.TestCase):
    def test_structure_updates_the_visible_editor(self):
        app = AppTest.from_file("app.py").run(timeout=40)
        self.assertFalse(app.exception)
        app.text_area(key="draft_preview").set_value(
            "Le vent souffle dans la vallée\nJe prends la route\n\nJe pars demain"
        ).run(timeout=40)
        app = click_by_label(app, "🔧 Structurer les paroles")
        self.assertFalse(app.exception)
        self.assertIn("[Verse 1]", app.session_state["draft_preview"])
        self.assertIn("[Chorus]", app.session_state["draft_preview"])

    def test_transfer_selects_composer_and_sets_custom_lyrics(self):
        app = AppTest.from_file("app.py").run(timeout=40)
        self.assertFalse(app.exception)
        app.text_area(key="draft_preview").set_value("Une chanson pour mon père").run(timeout=40)
        app = click_by_label(app, "↗ Utiliser ces paroles en mode Personnalisé")
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["song_mode"], "Personnalisé")
        self.assertEqual(app.session_state["melodia_active_tab"], "🎹  Composer")
        self.assertIn("Une chanson pour mon père", app.session_state["song_lyrics"])


if __name__ == "__main__":
    unittest.main()
