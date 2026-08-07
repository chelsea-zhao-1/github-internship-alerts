import requests

RAW_URL = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"


def fetch_markdown(repo: str, path: str, branch: str = "main") -> str:
    url = RAW_URL.format(repo=repo, branch=branch, path=path)
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch {url}: HTTP {response.status_code} - {response.text[:200]}"
        )
    return response.text
