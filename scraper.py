import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
word_counts = {}
subdomains = {}
longest_page = ("", 0)
unique_urls = set()
fingerprints = []
STOP_WORDS = {
    "a","about","above","after","again","against","all","am","an","and","any","are","aren't",
    "as","at","be","because","been","before","being","below","between","both","but","by",
    "can't","cannot","could","couldn't","did","didn't","do","does","doesn't","doing","don't",
    "down","during","each","few","for","from","further","had","hadn't","has","hasn't","have",
    "haven't","having","he","he'd","he'll","he's","her","here","here's","hers","herself",
    "him","himself","his","how","how's","i","i'd","i'll","i'm","i've","if","in","into","is",
    "isn't","it","it's","its","itself","let's","me","more","most","mustn't","my","myself",
    "no","nor","not","of","off","on","once","only","or","other","ought","our","ours","ourselves",
    "out","over","own","same","shan't","she","she'd","she'll","she's","should","shouldn't","so",
    "some","such","than","that","that's","the","their","theirs","them","themselves","then",
    "there","there's","these","they","they'd","they'll","they're","they've","this","those",
    "through","to","too","under","until","up","very","was","wasn't","we","we'd","we'll","we're",
    "we've","were","weren't","what","what's","when","when's","where","where's","which","while",
    "who","who's","whom","why","why's","with","won't","would","wouldn't","you","you'd","you'll",
    "you're","you've","your","yours","yourself","yourselves"
}

def get_chunks(words, k=3):
    chunks = set()
    for i in range(len(words) - k + 1):
        chunk = " ".join(words[i : i + k])
        chunks.add(hash(chunk))
    return chunks

def intersection(s1, s2):
    if not s1 or not s2: return 0
    return len(s1 & s2) / len(s1 | s2)

def scraper(url, resp):
    global longest_page, word_counts, subdomains, unique_urls, fingerprints

    parsed_url = urlparse(resp.url)
    actual_url = parsed_url._replace(fragment="").geturl()

    if resp.status != 200 or not resp.raw_response or actual_url in unique_urls: return []
    headers = resp.raw_response.headers
    try:
        content_len = int(headers.get("Content-Length", 0))
    except:
        content_len = 0

    # 10MB
    if content_len > 10_000_000:
        return []

    unique_urls.add(actual_url)
    soup = BeautifulSoup(resp.raw_response.content, "html.parser")

    text = soup.get_text()
    words = re.findall(r"[a-zA-Z]+", text.lower())
    filtered_words = [w for w in words if w not in STOP_WORDS and len(w) > 1]

    chunks = get_chunks(filtered_words)

    for fingerprint in fingerprints:
        if intersection(chunks, fingerprint) > 0.8:
            return []

    fingerprints.append(chunks)

    # count words
    for w in filtered_words:
        word_counts[w] = word_counts.get(w, 0) + 1

    # longest page
    if len(filtered_words) > longest_page[1]:
        longest_page = (actual_url, len(filtered_words))

    # subdomain counting
    hostname = parsed_url.hostname
    if hostname:
        subdomains[hostname] = subdomains.get(hostname, 0) + 1

    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    if resp.status != 200 or not resp.raw_response:
        return []

    # Use BeautifulSoup to find all <a> tags with href
    soup = BeautifulSoup(resp.raw_response.content, "html.parser")
    found_links = []
    for link in soup.find_all('a', href=True):
        # join relative URLs with base URL
        href = link['href'].strip()
        full_url = urljoin(resp.url, href)
        # remove anything after fragment
        clean_url = full_url.split('#')[0]
        if " " in clean_url or clean_url.count("http") > 1 or not clean_url.startswith("http"):
            continue
        found_links.append(clean_url)

    return found_links


def is_valid(url):
    # Decide whether to crawl this url or not.
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    if any(trap in url.lower() for trap in [
        "calendar",
        "/events/",
        "doku.php",
        "chemdb.ics.uci.edu",
        "cdb.ics.uci.edu",
    ]):
        return False

    # Block URLs that are too long
    if len(url) > 200:
        return False

    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        allowed_domains = [
            "ics.uci.edu",
            "cs.uci.edu",
            "informatics.uci.edu",
            "stat.uci.edu"
        ]

        if not parsed.hostname: return False
        is_allowed_domain = False
        for domain in allowed_domains:
            if parsed.hostname == domain or parsed.hostname.endswith('.' + domain):
                is_allowed_domain = True
                break
        if not is_allowed_domain: return False
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
        print ("TypeError for ", parsed)
        raise
