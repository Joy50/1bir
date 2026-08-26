from django.template.loader import get_template
from django.test import SimpleTestCase


class TrainingHomeTests(SimpleTestCase):
    def test_g_matter_template_uses_numbered_section_cards(self):
        source = get_template("training/training_home.html").template.source
        for label in (
            "Trg Plan",
            "IPFT State",
            "RET State",
            "Spd March State",
            "Aslt Course State",
            "Spl State",
        ):
            self.assertIn(label, source)
        self.assertEqual(source.count("section-card-link d-block h-100"), 6)
        self.assertEqual(source.count("card section-card h-100"), 6)
        for serial in range(1, 7):
            self.assertIn(f'data-serial="{serial:02d}"', source)
