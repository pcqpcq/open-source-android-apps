import os
import re
import requests
import json
from datetime import datetime

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}
URL_CACHE = {}

def get_final_url(url):
    """Follow redirects and return the final canonical URL. Returns (url, is_dead)."""
    if not url or not url.startswith('http'):
        return url, False
    if url in URL_CACHE:
        return URL_CACHE[url]
    
    # Skip badges and static assets
    if any(x in url for x in ['img.shields.io', 'badge', 'wikimedia.org', 'githubassets.com']):
        return url, False

    try:
        # Use a browser-like User-Agent to avoid being blocked by stores
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # Use GET with stream=True to follow redirects without downloading large files
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=10, stream=True)
        
        if response.status_code == 404:
            return url, True
            
        final_url = response.url.rstrip('/')
        
        # Special handling for GitHub: ensure it's the clean repo URL
        if 'github.com' in final_url:
            match = re.search(r'(https://github\.com/[^/]+/[^/]+)', final_url)
            if match:
                final_url = match.group(1)
        
        URL_CACHE[url] = (final_url, False)
        return final_url, False
    except Exception as e:
        print(f"Warning: Could not check redirect for {url}: {e}")
        return url, False

def get_github_repo_info(url):
    match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
    if not match:
        return None
    owner, repo = match.groups()
    # Remove trailing .git or /
    repo = repo.split('/')[0].split('.git')[0]
    api_url = f'https://api.github.com/repos/{owner}/{repo}'
    try:
        response = requests.get(api_url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            stars_count = data.get('stargazers_count', 0)
            stars = f"{stars_count/1000:.1f}k" if stars_count >= 1000 else str(stars_count)
            
            language = data.get('language')
            license_info = data.get('license')
            license_name = license_info.get('spdx_id') if license_info else None
            
            return {
                'stars': stars,
                'stars_val': stars_count,
                'language': language,
                'license': license_name,
                'url': data.get('html_url') # Canonical GitHub URL
            }
        elif response.status_code == 404:
            return {'is_dead': True}
        else:
            print(f"Error fetching {url}: {response.status_code}")
    except Exception as e:
        print(f"Exception for {url}: {e}")
    return None

def update_links_in_text(text):
    """Find all markdown links and update them if they redirect. Remove dead links."""
    # Improved regex to handle nested brackets (like image badges inside links)
    # Matches: [label](url) where label can contain [nested]
    link_pattern = r'\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\((https?://[^\s\)]+)\)'
    links = re.findall(link_pattern, text)
    if not links:
        return text
        
    new_links = []
    for label, url in links:
        final_url, is_dead = get_final_url(url)
        if not is_dead:
            new_links.append(f"[{label}]({final_url})")
    
    if not new_links:
        return "—"
    return " ".join(new_links)

def update_category_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    hot_apps = []
    
    def replace_main_table(match):
        app_link_part = match.group(1)
        url_match = re.search(r'\((https://github\.com/[^\)]+)\)', app_link_part)
        if not url_match:
            return match.group(0)
            
        url = url_match.group(1)
        description = match.group(2)
        
        info = get_github_repo_info(url)
        if info:
            if info.get('is_dead'):
                print(f"!!! Dead Repository found: {url}")
                return match.group(0) # Keep it but don't update

            new_stars = info['stars']
            new_lang = f"`{info['language']}`" if info['language'] else match.group(3)
            
            # Update GitHub link if it changed (e.g. renamed user/repo)
            new_app_link_part = app_link_part.replace(url, info['url'])
            
            # Update license if available and not generic
            new_license = match.group(4)
            if info['license'] and info['license'] != 'NOASSERTION':
                new_license = f"`{info['license']}`"
            
            # Update store links in the Download column
            new_download_col = update_links_in_text(match.group(6))
            
            # Check if it's a hot app (>10k)
            if info['stars_val'] >= 10000:
                app_name_match = re.search(r'\[\*\*([^*]+)\*\*\]', app_link_part)
                if app_name_match:
                    app_name = app_name_match.group(1)
                    hot_apps.append({
                        'name': app_name,
                        'url': info['url'],
                        'description': description.strip(),
                        'stars': new_stars
                    })
            
            return f"| {new_app_link_part} | {description} | {new_lang} | {new_license} | {new_stars} | {new_download_col} |"
        return match.group(0)

    def replace_featured_table(match):
        app_link_part = match.group(1)
        url_match = re.search(r'\((https://github\.com/[^\)]+)\)', app_link_part)
        if not url_match:
            return match.group(0)
            
        url = url_match.group(1)
        description = match.group(2)
        
        info = get_github_repo_info(url)
        if info and not info.get('is_dead'):
            new_stars = info['stars']
            new_lang = f"`{info['language']}`" if info['language'] else match.group(3)
            new_app_link_part = app_link_part.replace(url, info['url'])
            
            return f"| {new_app_link_part} | {description} | {new_lang} | {new_stars} |"
        return match.group(0)

    # Main table regex (6 columns)
    # Matches: | App | Desc | Lang | License | Stars | Download |
    main_table_pattern = r'^\| (\[\*\*.*?\].*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \|$'
    content = re.sub(main_table_pattern, replace_main_table, content, flags=re.MULTILINE)
    
    # Featured table regex (4 columns)
    # Matches: | App | Desc | Lang | Stars |
    featured_table_pattern = r'^\| (\[\*\*.*?\].*?) \| (.*?) \| (.*?) \| (.*?) \|$'
    content = re.sub(featured_table_pattern, replace_featured_table, content, flags=re.MULTILINE)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    return hot_apps

def update_readme(hot_apps):
    readme_path = 'README.md'
    with open(readme_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    in_hot_apps = False
    hot_apps_added = False
    
    for line in lines:
        if '## 🚀 Hot Apps' in line:
            in_hot_apps = True
            new_lines.append(line)
            new_lines.append("| App Name | Description | ⭐ Stars |\n")
            new_lines.append("| :--- | :--- | :---: |\n")
            # Sort hot apps by stars
            def get_stars_val(app):
                s = app['stars'].lower()
                if 'k' in s:
                    try:
                        return float(s.replace('k', '')) * 1000
                    except:
                        return 0
                try:
                    return float(s)
                except:
                    return 0
            
            sorted_hot = sorted(hot_apps, key=get_stars_val, reverse=True)
            # Remove duplicates
            seen = set()
            for app in sorted_hot:
                if app['url'] not in seen:
                    new_lines.append(f"| [**{app['name']}**]({app['url']}) | {app['description']} | {app['stars']} |\n")
                    seen.add(app['url'])
            hot_apps_added = True
            continue
        
        if in_hot_apps:
            if line.startswith('##') or line.startswith('# '):
                in_hot_apps = False
                new_lines.append(line)
            continue
        
        new_lines.append(line)

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    all_hot_apps = []
    categories_dir = 'categories'
    for filename in os.listdir(categories_dir):
        if filename.endswith('.md'):
            print(f"Updating {filename}...")
            hot = update_category_file(os.path.join(categories_dir, filename))
            all_hot_apps.extend(hot)
    
    print("Updating README...")
    update_readme(all_hot_apps)
    print("Done!")
