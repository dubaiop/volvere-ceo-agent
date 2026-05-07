"""HubSpot API client — contacts, companies, deals."""

import requests
from config import HUBSPOT_API_KEY, HUBSPOT_BASE_URL


def _headers() -> dict:
    return {"Authorization": f"Bearer {HUBSPOT_API_KEY}", "Content-Type": "application/json"}


def get_pipeline_summary() -> dict:
    """Returns deal counts and total value by stage."""
    url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/deals"
    params = {"limit": 50, "properties": "dealname,amount,dealstage,closedate"}
    resp = requests.get(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    deals = resp.json().get("results", [])

    stages: dict[str, dict] = {}
    for d in deals:
        p = d.get("properties", {})
        stage = p.get("dealstage", "unknown")
        amount = float(p.get("amount") or 0)
        if stage not in stages:
            stages[stage] = {"count": 0, "value": 0}
        stages[stage]["count"] += 1
        stages[stage]["value"] += amount

    return {"stages": stages, "total_deals": len(deals), "total_value": sum(s["value"] for s in stages.values())}


def get_recent_contacts(limit: int = 10) -> list[dict]:
    url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts"
    params = {"limit": limit, "properties": "firstname,lastname,email,company,jobtitle,lifecyclestage", "sort": "-createdate"}
    resp = requests.get(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json().get("results", [])


def get_recent_deals(limit: int = 10) -> list[dict]:
    url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/deals"
    params = {"limit": limit, "properties": "dealname,amount,dealstage,closedate", "sort": "-createdate"}
    resp = requests.get(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json().get("results", [])
