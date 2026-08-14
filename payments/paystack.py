import requests
from django.conf import settings


class Paystack:
    PAYSTACK_SK = settings.PAYSTACK_SECRET_KEY
    base_url = "https://api.paystack.co/"

    def verify_payment(self, ref, *args, **kwargs):
        path = f"transaction/verify/{ref}"
        headers = {
            "Authorization": f"Bearer {self.PAYSTACK_SK}",
            "Content-Type": "application/json",
        }
        url = self.base_url + path

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("status"):
                return True, response_data.get("data", {})
            
            return False, {"message": response_data.get("message", "Verification failed")}
        except requests.RequestException:
            return False, {"message": "Network connection error while reaching Paystack."}