import tomllib
from pathlib import Path
import requests

secrets_path = Path('test-python/.streamlit/secrets.toml')
with secrets_path.open('rb') as fh:
    secrets = tomllib.load(fh)

jira = secrets['JIRA']
url = jira['API_URL'].rstrip('/') + '/rest/api/3/search/jql'
params = {
    'jql': jira['JQL'],
    'maxResults': 3,
    'fields': 'summary,assignee,status,created,updated,resolutiondate,priority,project',
}
resp = requests.get(url, auth=(jira['EMAIL'], jira['TOKEN']), params=params, timeout=30)
print(resp.status_code)
print(resp.text[:4000])
