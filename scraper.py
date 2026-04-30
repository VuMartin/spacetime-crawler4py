import re
import json
import os
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

STATS_FILE = "stats.json"

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            data = json.load(f)
            return (
                data.get("word_counts", {}),
                tuple(data.get("longest_page", ["", 0])),
                data.get("subdomains", {}),
                set(data.get("unique_urls", []))
            )
    return {}, ("", 0), {}, set()

word_counts, longest_page, subdomains, unique_urls = load_stats()
page_counter = 0

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "was", "are", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "not", "no", "nor", "so", "yet", "both", "either", "neither",
    "this", "that", "these", "those", "it", "its", "as", "if", "then"
}

def save_stats():
    with open(STATS_FILE, "w") as f:
        json.dump({
            "word_counts": word_counts,
            "longest_page": list(longest_page),
            "subdomains": subdomains,
            "unique_urls": list(unique_urls)
        }, f)

def scraper(url, resp):
    global longest_page, page_counter

    actual_url = resp.url

    if resp.status != 200 or not resp.raw_response:
        return []

    if actual_url in unique_urls:
        return []

    unique_urls.add(actual_url)

    soup = BeautifulSoup(resp.raw_response.content, "html.parser")

    text = soup.get_text()
    words = [w for w in re.findall(r"\w+", text.lower()) if w not in STOP_WORDS]

    for w in words:
        word_counts[w] = word_counts.get(w, 0) + 1

    # Track longest page
    if len(words) > longest_page[1]:
        longest_page = (actual_url, len(words))

    # Track subdomains
    parsed = urlparse(actual_url)
    hostname = parsed.hostname
    if hostname:
        subdomains[hostname] = subdomains.get(hostname, 0) + 1

    # Save every 50 pages
    page_counter += 1
    if page_counter % 50 == 0:
        save_stats()

    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]


def extract_next_links(url, resp):
    if resp.status != 200 or not resp.raw_response:
        return []

    soup = BeautifulSoup(resp.raw_response.content, "html.parser")
    found_links = []
    for link in soup.find_all('a', href=True):
        full_url = urljoin(resp.url, link['href'])
        clean_url = full_url.split('#')[0]
        found_links.append(clean_url)

    return found_links


def is_valid(url):
    try:
        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            return False

        # Block trap query parameters
        query = parsed.query.lower()
        trap_params = ["action=", "date=", "calendar=", "session=", "sid=", "filter="]
        if any(p in query for p in trap_params):
            return False

        # Block very long URLs
        if len(url) > 200:
            return False

        # Block repeated path segments (crawler traps)
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) != len(set(path_parts)):
            return False

        # Only allow the four required domains
        allowed_domains = [
            "ics.uci.edu",
            "cs.uci.edu",
            "informatics.uci.edu",
            "stat.uci.edu"
        ]
        if not (parsed.hostname and parsed.hostname.endswith(tuple(allowed_domains))):
            return False

        # Block non-HTML file extensions
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print("TypeError for ", parsed)
        raise