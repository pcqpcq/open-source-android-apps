import os
import re
import requests
import json
from datetime import datetime

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}

def get_github_stars(url):
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
            stars = response.json().get('stargazers_count', 0)
            if stars >= 1000:
                return f"{stars/1000:.1f}k"
            return str(stars)
        else:
            print(f"Error fetching {url}: {response.status_code}")
    except Exception as e:
        print(f"Exception for {url}: {e}")
    return None

def update_category_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    hot_apps = []
    
    # Regex to match table rows with GitHub links
    # | [**Name**](URL) | Description | Language | License | ⭐ Stars | Download |
    # OR for featured: | [**Name**](URL) | Description | Language | ⭐ Stars |
    
    def replace_stars(match):
        app_link_part = match.group(1)
        url = re.search(r'\((https://github\.com/[^\)]+)\)', app_link_part).group(1)
        description = match.group(2)
        language = match.group(3)
        
        new_stars = get_github_stars(url)
        if new_stars:
            # Check if it's a hot app (>10k)
            star_val = float(new_stars.replace('k', '')) * 1000 if 'k' in new_stars else float(new_stars)
            if star_val >= 10000:
                app_name = re.search(r'\[\*\*([^*]+)\*\*\]', app_link_part).group(1)
                hot_apps.append({
                    'name': app_name,
                    'url': url,
                    'description': description.strip(),
                    'stars': new_stars
                })
            
            # Return updated row
            if match.group(5): # Main table (6 columns)
                return f"| {app_link_part} | {description} | {language} | {match.group(4)} | {new_stars} | {match.group(5)} |"
            else: # Featured table (4 columns)
                return f"| {app_link_part} | {description} | {language} | {new_stars} |"
        return match.group(0)

    # Main table regex (6 columns)
    main_table_pattern = r'\| (\[\*\*.*?\].*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \|'
    content = re.sub(main_table_pattern, replace_stars, content)
    
    # Featured table regex (4 columns)
    featured_table_pattern = r'\| (\[\*\*.*?\].*?) \| (.*?) \| (.*?) \| (.*?) \|(?!\s*\|)'
    # Note: This might need refinement to avoid matching the main table. 
    # But since we already processed the main table, we can be careful.
    
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
            sorted_hot = sorted(hot_apps, key=lambda x: float(x['stars'].replace('k', '')) if 'k' in x['stars'] else float(x['stars']), reverse=True)
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
