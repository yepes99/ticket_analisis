import requests

url = "https://avantio.atlassian.net/rest/api/3/myself"

r = requests.get(url)
print(r.status_code)
print(r.text)