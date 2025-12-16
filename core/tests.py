from django.test import TestCase

class AffiliateQRViewTests(TestCase):
    def test_qr_view_returns_png(self):
        response = self.client.get("/qr/affiliate/test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertGreater(len(response.content), 0)

    def test_qr_root_uses_base_url(self):
        response = self.client.get("/qr")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertGreater(len(response.content), 0)
