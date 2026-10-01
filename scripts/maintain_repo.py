import os
import re

from github_utils import get_github_repo_info


def update_links_in_text(text):
    """Rebuild a Download-column cell.

    GitHub links are verified through the API: dead repositories are dropped
    and live ones canonicalised to the repo root (the API's html_url is the
    canonical URL, so no separate redirect-following request is needed).
    Non-GitHub links (Play Store, F-Droid, ...) are stable and kept as-is.
    """
    # Improved regex to handle nested brackets (like image badges inside links)
    # Matches: [label](url) where label can contain [nested]
    link_pattern = r'\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\((https?://[^\s\)]+)\)'
    links = re.findall(link_pattern, text)
    if not links:
        return "—"
        
    new_links = []
    for label, url in links:
        if 'github.com' in url:
            info = get_github_repo_info(url)
            if not info or info.get('is_dead'):
                continue
            url = info['url']
        new_links.append(f"[{label}]({url})")
    
    if not new_links:
        return "—"
    return " ".join(new_links)

def update_category_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    hot_apps = []
    
    def replace_main_table(match):
        app_link_part = match.group(1).strip()
        url_match = re.search(r'\((https://github\.com/[^\)]+)\)', app_link_part)
        if not url_match:
            return match.group(0)
            
        url = url_match.group(1)
        description = match.group(2).strip()
        
        info = get_github_repo_info(url)
        if info:
            if info.get('is_dead'):
                print(f"!!! Dead Repository found: {url}")
                return match.group(0)

            new_stars = info['stars']
            new_lang = f"`{info['language']}`" if info['language'] else match.group(3).strip()
            
            # Update GitHub link if it changed
            new_app_link_part = app_link_part.replace(url, info['url'])
            
            # Update license
            new_license = match.group(4).strip()
            if info['license'] and info['license'] != 'NOASSERTION':
                new_license = f"`{info['license']}`"
            
            # Update store links in the Download column
            # If the current column 6 is just a number (corrupted stars), ignore it
            current_download = match.group(6).strip()
            new_download_col = update_links_in_text(current_download)
            
            # Check if it's a hot app (>10k)
            if info['stars_val'] >= 10000:
                app_name_match = re.search(r'\[\*\*([^*]+)\*\*\]', app_link_part)
                if app_name_match:
                    app_name = app_name_match.group(1)
                    hot_apps.append({
                        'name': app_name,
                        'url': info['url'],
                        'description': description,
                        'stars': new_stars
                    })
            
            return f"| {new_app_link_part} | {description} | {new_lang} | {new_license} | {new_stars} | {new_download_col} |"
        return match.group(0)

    def replace_featured_table(match):
        app_link_part = match.group(1).strip()
        url_match = re.search(r'\((https://github\.com/[^\)]+)\)', app_link_part)
        if not url_match:
            return match.group(0)
            
        url = url_match.group(1)
        description = match.group(2).strip()
        
        info = get_github_repo_info(url)
        if info and not info.get('is_dead'):
            new_stars = info['stars']
            new_lang = f"`{info['language']}`" if info['language'] else match.group(3).strip()
            new_app_link_part = app_link_part.replace(url, info['url'])
            
            return f"| {new_app_link_part} | {description} | {new_lang} | {new_stars} |"
        return match.group(0)

    # Split content into sections to apply different table logic
    sections = re.split(r'(## .*?\n)', content)
    new_sections = []
    current_header = ""
    
    for section in sections:
        if section.startswith('## '):
            current_header = section
            new_sections.append(section)
            continue
            
        if "Featured Apps" in current_header:
            # 4-column table
            pattern = r'^\| (\[\*\*[^|]*?\].*?) \| ([^|]*?) \| ([^|]*?) \| ([^|]*?) \|$'
            section = re.sub(pattern, replace_featured_table, section, flags=re.MULTILINE)
        else:
            # 6-column table
            pattern = r'^\| (\[\*\*[^|]*?\].*?) \| ([^|]*?) \| ([^|]*?) \| ([^|]*?) \| ([^|]*?) \| ([^|]*?) \|$'
            section = re.sub(pattern, replace_main_table, section, flags=re.MULTILINE)
        new_sections.append(section)
        
    content = "".join(new_sections)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    return hot_apps

def count_apps_in_category(file_path):
    """Count open-source app rows in a category file's main table.

    Stops at the first sub-section (### Non-Open-Source / ### How to Contribute)
    so non-open-source entries are excluded from the total.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    count = 0
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('### '):
            break
        if stripped.startswith('| App Name |'):
            in_table = True
            continue
        if in_table:
            if stripped.startswith('| [**'):
                count += 1
            elif not stripped.startswith('|'):
                in_table = False
    return count


def _stars_value(stars_str):
    """Convert a display string like '12.7k' or '936' to a numeric value for sorting."""
    s = (stars_str or '0').lower()
    if 'k' in s:
        try:
            return float(s.replace('k', '')) * 1000
        except ValueError:
            return 0
    try:
        return float(s)
    except ValueError:
        return 0


def update_readme(hot_apps, category_counts):
    """Rewrite the Hot Apps section, refresh per-category counts, and the Total badge."""
    readme_path = 'README.md'
    with open(readme_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    total_apps = sum(category_counts.values())

    new_lines = []
    in_hot_apps = False

    for line in lines:
        # Refresh the "Total Apps" badge in the header.
        line = re.sub(r'(Total%20Apps-)\d+(?=-brightgreen)',
                      lambda m: f"{m.group(1)}{total_apps}", line)

        # Refresh the Count column of the categories table.
        # Rows look like: | [📺 X](categories/foo.md) | desc | N |
        if '](categories/' in line:
            fn_match = re.search(r'\]\(categories/([^)]+\.md)\)', line)
            if fn_match and fn_match.group(1) in category_counts:
                count = category_counts[fn_match.group(1)]
                line = re.sub(r'\d+(?=\s*\|\s*$)', str(count), line)

        if '## 🚀 Hot Apps' in line:
            in_hot_apps = True
            new_lines.append(line)
            new_lines.append("| App Name | Description | ⭐ Stars |\n")
            new_lines.append("| :--- | :--- | :---: |\n")
            # Sort hot apps by stars (descending), de-duplicating by repo URL.
            sorted_hot = sorted(hot_apps, key=lambda a: _stars_value(a['stars']), reverse=True)
            seen = set()
            for app in sorted_hot:
                if app['url'] not in seen:
                    new_lines.append(f"| [**{app['name']}**]({app['url']}) | {app['description']} | {app['stars']} |\n")
                    seen.add(app['url'])
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
    if not os.environ.get('GITHUB_TOKEN'):
        print("Warning: GITHUB_TOKEN is not set. Unauthenticated GitHub API "
              "requests are limited to 60/hour, which is not enough for a "
              "full run (~1 request per app); the run may fail partway through.\n")

    all_hot_apps = []
    category_counts = {}
    categories_dir = 'categories'
    for filename in sorted(os.listdir(categories_dir)):
        if filename.endswith('.md'):
            print(f"Updating {filename}...")
            file_path = os.path.join(categories_dir, filename)
            hot = update_category_file(file_path)
            all_hot_apps.extend(hot)
            category_counts[filename] = count_apps_in_category(file_path)

    print("Updating README...")
    update_readme(all_hot_apps, category_counts)
    print(f"Done! Total apps: {sum(category_counts.values())}")
