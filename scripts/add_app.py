import os
import re
import sys

from github_utils import get_github_repo_info

def get_categories():
    categories_dir = 'categories'
    files = [f for f in os.listdir(categories_dir) if f.endswith('.md')]
    return sorted(files)

def add_app(name=None, repo=None, store=None, desc=None, category=None):
    print("--- Add New Open Source Android App ---")
    
    # 1. Select Category
    categories = get_categories()
    if not category:
        print("\nAvailable Categories:")
        for i, cat in enumerate(categories):
            print(f"{i+1}. {cat.replace('.md', '')}")
        
        try:
            cat_idx = int(input("\nSelect category number: ")) - 1
            if cat_idx < 0 or cat_idx >= len(categories):
                print("Invalid selection.")
                return
            category_file = os.path.join('categories', categories[cat_idx])
        except ValueError:
            print("Please enter a number.")
            return
    else:
        # Support both "tools" and "tools.md"
        if not category.endswith('.md'):
            category += '.md'
        if category not in categories:
            print(f"Category {category} not found.")
            return
        category_file = os.path.join('categories', category)

    # 2. Input App Details
    # In non-interactive mode (like GitHub Actions), we must not call input()
    is_interactive = not (name and repo)
    
    app_name = name if name else input("App Name: ").strip()
    repo_url = repo if repo else input("GitHub Repository URL: ").strip()
    
    if is_interactive:
        store_url = store if store else input("Store/Download URL (optional, press Enter for none): ").strip()
        custom_desc = desc if desc else input("Description (optional, press Enter to use GitHub description): ").strip()
    else:
        store_url = store if store else ""
        custom_desc = desc if desc else ""

    print(f"\nFetching repository info for {repo_url}...")
    info = get_github_repo_info(repo_url)
    if not info or info.get('is_dead'):
        print("Could not fetch GitHub info. The repository may not exist or is not a GitHub repo. Please check the URL.")
        return

    description = custom_desc if custom_desc else info['description']
    if not description:
        description = "No description provided."

    # Language/license: keep backticks to match the table style used elsewhere.
    # GitHub returns null license or 'NOASSERTION' when the license can't be mapped.
    language = info['language'] or 'Unknown'
    license_name = info['license']
    if not license_name or license_name == 'NOASSERTION':
        license_name = 'Not specified'

    # 3. Format Download Link
    download_val = "—"
    if store_url:
        if 'play.google.com' in store_url:
            download_val = f"[![Google Play](https://upload.wikimedia.org/wikipedia/commons/7/78/Google_Play_Store_badge_EN.svg)]({store_url})"
        elif 'f-droid.org' in store_url:
            download_val = f"[![F-Droid](https://f-droid.org/badge/get-it-on.svg)]({store_url})"
        else:
            download_val = f"[![Download](https://img.shields.io/badge/Download-APK-blue)]({store_url})"

    # 4. Create Table Row
    # | App Name | Description | Language | License | ⭐ Stars | Download |
    new_row = f"| [**{app_name}**]({info['url']}) | {description} | `{language}` | `{license_name}` | {info['stars']} | {download_val} |"

    # 5. Insert into File
    with open(category_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the "All Apps" section or the main table
    table_start_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('| App Name |'):
            table_start_idx = i
            
    if table_start_idx == -1:
        print("Could not find the apps table in the file.")
        return

    # Find where the table ends or where to insert alphabetically
    insert_pos = -1
    for i in range(table_start_idx + 2, len(lines)):
        line = lines[i].strip()
        if not line.startswith('|'):
            insert_pos = i
            break
        
        # Extract app name from existing row for alphabetical comparison
        match = re.search(r'\[\*\*(.*?)\*\*\]', line)
        if match:
            existing_name = match.group(1).lower()
            if app_name.lower() < existing_name:
                insert_pos = i
                break
    
    if insert_pos == -1:
        insert_pos = len(lines)

    lines.insert(insert_pos, new_row + "\n")

    with open(category_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"\nSuccessfully added {app_name} to {os.path.basename(category_file)}!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Add a new app to the collection.')
    parser.add_argument('--name', help='App Name')
    parser.add_argument('--repo', help='GitHub Repository URL')
    parser.add_argument('--store', help='Store/Download URL')
    parser.add_argument('--desc', help='Custom Description')
    parser.add_argument('--category', help='Category filename (e.g. tools.md)')
    
    args = parser.parse_args()
    
    try:
        if args.name or args.repo or args.category:
            add_app(name=args.name, repo=args.repo, store=args.store, desc=args.desc, category=args.category)
        else:
            add_app()
    except KeyboardInterrupt:
        print("\nCancelled.")
