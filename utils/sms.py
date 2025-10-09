import os
import requests
import httpx
# from decouple import config


BEEM_API_KEY = os.getenv("BEEM_API_KEY", default=os.getenv("BEEM_AFRICA_API_KEY"))
BEEM_SECRET_KEY = os.getenv("BEEM_SECRET_KEY", default=os.getenv("BEEM_AFRICA_SECRET_KEY"))


BASE_URL = "https://apisms.beem.africa/v1/send"
SOURCE_ADDR = "KKKT-KIFURU"


def format_phone(phone: str) -> str:
    """
    Normalize phone numbers to Beem format: 255XXXXXXXXX
    - Strips spaces, dashes, etc.
    - If starts with 0, replace with 255.
    - If already starts with 255, keep it.
    """
    phone = phone.strip().replace(" ", "").replace("-", "")

    if phone.startswith("0"):
        return "255" + phone[1:]
    elif phone.startswith("+"):
        return phone[1:]  # strip +
    elif phone.startswith("255"):
        return phone
    else:
        return "255" + phone

async def send_sms_single(message: str, dest_addr: str):
    """
    Send an SMS to a single recipient asynchronously.
    """
    formatted_phone = format_phone(dest_addr)

    payload = {
        "source_addr": SOURCE_ADDR,
        "schedule_time": "",
        "encoding": 0,
        "message": message,
        "recipients": [
            {
                "recipient_id": "1",
                "dest_addr": formatted_phone
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            BASE_URL,
            auth=(BEEM_API_KEY, BEEM_SECRET_KEY),
            headers={"Content-Type": "application/json"},
            json=payload
        )
        return response.json()


async def send_sms_bulk(message: str, dest_addrs: list[str]):
    """
    Send an SMS to multiple recipients asynchronously.
    """
    recipients = [
        {"recipient_id": str(i+1), "dest_addr": format_phone(phone)}
        for i, phone in enumerate(dest_addrs)
    ]

    payload = {
        "source_addr": SOURCE_ADDR,
        "schedule_time": "",
        "encoding": 0,
        "message": message,
        "recipients": recipients
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            BASE_URL,
            auth=(BEEM_API_KEY, BEEM_SECRET_KEY),
            headers={"Content-Type": "application/json"},
            json=payload
        )
        return response.json()
    

