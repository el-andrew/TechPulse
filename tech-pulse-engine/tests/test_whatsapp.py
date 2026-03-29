from __future__ import annotations

import unittest

from app.formatters.whatsapp import format_whatsapp_channel
from app.parsers.models import CollectedItem


class WhatsAppFormattingTests(unittest.TestCase):
    def test_channel_format_uses_location_and_application_url(self) -> None:
        item = CollectedItem(
            title="COSTECH Innovation Grant",
            description="Funding for innovators in Tanzania building practical digital products.",
            source_name="COSTECH",
            source_type="html",
            source_url="https://costech.or.tz/Funding",
            link="https://costech.or.tz/Funding",
            application_url="https://costech.or.tz/Funding",
            category_hint="grant",
            africa_relevance_weight=0.95,
            category="Grant",
            country="Tanzania",
            audience_scope="tanzania",
            issuer_name="Tanzania Commission for Science and Technology",
            location_text="Dar es Salaam, Tanzania",
        )

        rendered = format_whatsapp_channel(item)
        self.assertIn("Dar es Salaam, Tanzania", rendered)
        self.assertIn("Apply here: https://costech.or.tz/Funding", rendered)
        self.assertIn("#TechPulseTanzania", rendered)


if __name__ == "__main__":
    unittest.main()
