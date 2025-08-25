import requests
from ..config import cfg

def _auth_headers():
    if not cfg.uphold_pat:
        raise RuntimeError("UPHOLD_PAT not configured.")
    return {"Authorization": f"Bearer {cfg.uphold_pat}", "Content-Type": "application/json"}

def create_market_exchange(from_currency: str, to_currency: str, amount: str):
    # First, get the user's cards to find the source card ID
    me_url = f"{cfg.uphold_api}/v0/me"
    me_response = requests.get(me_url, headers=_auth_headers(), timeout=15)
    me_response.raise_for_status()
    cards = me_response.json().get("cards", [])
    
    # Find the card that matches the 'from_currency'
    source_card = next((card for card in cards if card['currency'] == from_currency), None)
    if not source_card:
        raise RuntimeError(f"No card found for currency {from_currency} in Uphold account.")
    card_id = source_card["id"]

    # Create the transaction draft
    draft_url = f"{cfg.uphold_api}/v0/me/cards/{card_id}/transactions"
    draft_payload = {"denomination": {"amount": str(amount), "currency": from_currency}, "destination": to_currency}
    draft_response = requests.post(draft_url, headers=_auth_headers(), json=draft_payload, timeout=15)
    draft_response.raise_for_status()
    draft = draft_response.json()
    
    tx_id = draft.get("id")
    if not tx_id:
        raise RuntimeError(f"Uphold draft failed: {draft}")

    # Commit the transaction
    commit_url = f"{cfg.uphold_api}/v0/me/cards/{card_id}/transactions/{tx_id}/commit"
    commit_response = requests.post(commit_url, headers=_auth_headers(), timeout=15)
    commit_response.raise_for_status()
    return commit_response.json()
