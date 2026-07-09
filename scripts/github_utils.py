"""Shared helpers for the repository maintenance scripts.

Centralises GitHub API access so add_app.py and maintain_repo.py do not
duplicate the same request logic (see the project's DRY contribution rule).
"""

import os
import re
import requests

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}


def get_github_repo_info(url):
    """Fetch metadata for a GitHub repository URL.

    Returns a dict with stars/stars_val/language/license/url/description,
    a {'is_dead': True} dict when the repo returns 404, or None on failure.
    """
    match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
    if not match:
        return None
    owner, repo = match.groups()
    # Strip trailing slashes, ".git", and any path segments after the repo name.
    repo = repo.split('/')[0].split('.git')[0]
    api_url = f'https://api.github.com/repos/{owner}/{repo}'
    try:
        response = requests.get(api_url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            stars_count = data.get('stargazers_count', 0) or 0
            stars = f"{stars_count/1000:.1f}k" if stars_count >= 1000 else str(stars_count)
            license_info = data.get('license')
            license_name = license_info.get('spdx_id') if license_info else None
            return {
                'stars': stars,
                'stars_val': stars_count,
                'language': data.get('language'),
                'license': license_name,
                'url': data.get('html_url'),  # Canonical GitHub URL
                'description': data.get('description', '') or '',
            }
        elif response.status_code == 404:
            return {'is_dead': True}
        else:
            print(f"Error fetching {url}: {response.status_code}")
    except Exception as e:
        print(f"Exception for {url}: {e}")
    return None
