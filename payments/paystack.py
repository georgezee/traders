# payments/paystack.py
import requests
from django.conf import settings

class Paystack:
    base_url = "https://api.paystack.co/"

    def initialize(self, *, email, callback_url, reference, amount=None, metadata=None, plan_code=None):
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        data = {
            "email": email,
            "callback_url": callback_url,
            "currency": "ZAR",
            "reference": reference,
        }
        if plan_code:
            data["plan"] = plan_code
        if amount is not None:
            data["amount"] = str(amount)
        elif not plan_code:
            raise ValueError("Amount is required when initializing a once-off payment.")
        if metadata:
            data["metadata"] = metadata

        try:
            response = requests.post(
                self.base_url + "transaction/initialize",
                json=data,
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            message = str(exc)
            if exc.response is not None:
                try:
                    error_payload = exc.response.json()
                    message = error_payload.get("message", message)
                except ValueError:
                    message = exc.response.text or message
            return {"status": False, "message": message}
        except requests.RequestException as exc:
            return {"status": False, "message": str(exc)}

        try:
            payload = response.json()
        except ValueError:
            return {"status": False, "message": "Unexpected response from Paystack."}

        return payload

    def verify_payment(self, reference):
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        response = requests.get(self.base_url + f"transaction/verify/{reference}", headers=headers)
        json_resp = response.json()
        return json_resp.get("status"), json_resp.get("data", {})
