import json
import tomllib
from pathlib import Path

import requests


def load_jira_config():
    secrets_path = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
    with secrets_path.open("rb") as fh:
        secrets = tomllib.load(fh)
    return secrets["JIRA"]


def fetch_jira_issues():
    jira = load_jira_config()
    api_url = jira["API_URL"].rstrip("/")
    url = f"{api_url}/rest/api/2/search"

    params = {
        "jql": jira["JQL"],
        "maxResults": 5,
        "fields": "summary,assignee,status,created,updated,resolutiondate,priority,project",
    }

    try:
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            auth=(jira["EMAIL"], jira["TOKEN"]),
            params=params,
            timeout=30,
        )
        print("status", response.status_code)
        print(response.text[:4000])
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        print("RequestException", exc)
        raise


if __name__ == "__main__":
    payload = fetch_jira_issues()
    print("status: ok")
    print("total", payload.get("total", 0))
    print("issues", len(payload.get("issues", [])))
    for issue in payload.get("issues", [])[:3]:
        fields = issue.get("fields", {})
        print({
            "key": issue.get("key"),
            "summary": fields.get("summary"),
            "status": fields.get("status", {}).get("name"),
            "assignee": fields.get("assignee", {}).get("displayName"),
            "created": fields.get("created"),
            "project": fields.get("project", {}).get("name"),
        })
