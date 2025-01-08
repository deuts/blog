import os
import requests
import json
import time
import re
import markdownify  # Importing markdownify for HTML to Markdown conversion
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta

# Load configuration
with open("gts-config.json", "r") as config_file:
    config = json.load(config_file)

BASE_URL = config["BASE_URL"]
ACCESS_TOKEN = config["ACCESS_TOKEN"]
ACCOUNT_ID = config["ACCOUNT_ID"]
EARLIEST_DATE = config["EARLIEST_DATE"]
OUTPUT_DIR = config["OUTPUT_DIR"]

# Headers for API Authorization
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Convert EARLIEST_DATE to datetime object for comparison
earliest_datetime = datetime.fromisoformat(EARLIEST_DATE.replace("Z", "+00:00"))

# Function to convert created_at to Manila time
def to_manila_time(utc_time):
    utc_datetime = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
    manila_tz = timezone(timedelta(hours=8))
    return utc_datetime.astimezone(manila_tz)

# Function to format mentions and hashtags in the status text
def format_status_content(content):
    # Replace newlines (\n) with markdown-friendly format, keeping \n as is
    content = content.replace("\n", "\n")  # Keeps newline as is (no change)

    # Convert plain URLs to markdown links
    content = convert_links_to_markdown(content)

    # Convert mentions to markdown links
    content = re.sub(r"@(\w+)@([\w\.]+)", r"[@\1](https://\2/@\1)", content)

    # Convert hashtags to markdown links without escaping the #
    content = re.sub(
        r"#(\w+)",  # Match hashtags
        r"[#\1](https://fediverse-explorer.stefanbohacek.dev/?tag=\1)",  # Format as a markdown link
        content,
    )
    
    # Ensure the content is valid HTML before markdown conversion
    content = ensure_valid_html(content)

    return content


# Function to convert plain URLs in content to markdown links
def convert_links_to_markdown(content):
    # Convert plain URLs to markdown links with the domain as the text
    def replace_url_with_link(match):
        url = match.group(0)  # Get the full URL
        domain = urlparse(url).netloc  # Extract the domain
        return f"[{domain}/&infin;]({url})"
    
    content = re.sub(r'https?://[^\s]+', replace_url_with_link, content)
    return content

# Function to ensure content is valid HTML before conversion
def ensure_valid_html(content):
    # Check if the content is valid HTML or contains tags
    if "<" in content and ">" in content:
        return markdownify.markdownify(content)
    else:
        return content

# Save status to markdown file
def save_status_as_markdown(status):
    # Extract required fields
    id = status["id"]
    created_at = status["created_at"]
    manila_datetime = to_manila_time(created_at)
    converted_date = manila_datetime.isoformat()
    slug_date = manila_datetime.strftime("%Y-%m-%d-%H-%M-%S")
    slug = f"{slug_date}-{id}"
    link = status["url"]

    # Use get to safely fetch text and handle missing cases
    status_text = status.get("text", "")
    if not status_text:
        print(f"Skipping status {id} (created at {created_at}) - no text content.")
        return

    # Keep the `\n` in the status_text as it is (single line for frontmatter)
    status_text_frontmatter = status_text.replace("\n", " ")  # Remove line breaks for frontmatter

    # Format the body content (status_content) with proper markdown formatting (without changing \n)
    status_content = format_status_content(status_text)

    # Generate filename and file path
    filename = f"{slug}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # Construct content for the markdown file
    markdown_content = f"""---
title: "@deuts@deuts.one {id}"
date: {converted_date}
aside_type: gotosocial
slug: {slug}
link: {link}
gtsid: {id}
status: "{status_text_frontmatter}"
---

{status_content}
"""

    # Save to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"Saved: {filepath}")

# Function to fetch statuses with pagination
def fetch_statuses(account_id, max_id=None):
    url = f"{BASE_URL}/api/v1/accounts/{account_id}/statuses"
    params = {"limit": 20}  # Adjust limit as needed
    if max_id:
        params["max_id"] = max_id

    response = requests.get(url, headers=headers, params=params)

    # Handle rate limiting
    if response.status_code == 429:
        reset_time = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
        wait_time = reset_time - int(time.time())
        print(f"Rate limit reached. Waiting for {wait_time} seconds...")
        time.sleep(wait_time)
        return fetch_statuses(account_id, max_id)  # Retry after wait

    if response.status_code != 200:
        print(f"Error fetching statuses: {response.status_code} - {response.text}")
        return [], None

    statuses = response.json()

    # Update max_id for pagination
    if statuses:
        next_max_id = statuses[-1]["id"]  # Use the ID of the last status for the next page
    else:
        next_max_id = None

    return statuses, next_max_id

# Main Logic
def main():
    max_id = None
    while True:
        statuses, max_id = fetch_statuses(ACCOUNT_ID, max_id)
        if not statuses:
            print("No more statuses to fetch.")
            break

        for status in statuses:
            # Convert created_at to datetime object for comparison
            created_at = status["created_at"]
            created_at_datetime = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

            if created_at_datetime < earliest_datetime:
                print(f"Skipping status {status['id']} (created at {created_at}) - earlier than {EARLIEST_DATE}.")
                continue

            save_status_as_markdown(status)

        if not max_id:
            print("Reached the end of available statuses.")
            break

if __name__ == "__main__":
    main()