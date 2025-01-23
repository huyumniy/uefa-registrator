import requests

url = "https://104.18.27.241/realmadrid_champions/en_US/entradas/evento/39300/session/2245485/select?viewCode=V_blockmap_view"

# Set the Host header manually
headers = {
    "Host": "tickets.realmadrid.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
}

response = requests.get(url, headers=headers, verify=False)  # Use `verify=False` to bypass SSL verification for IP
print(response.status_code)
print(response.text)
