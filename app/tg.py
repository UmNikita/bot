import requests


TG_TOKEN = "6380036724:AAGuMCmgH54Dr5mpRb1f65h5Z_iZssP8glI"
CHAT_ID = "1338703505"


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=10
    )

    response.raise_for_status()