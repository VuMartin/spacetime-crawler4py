import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
word_counts = {}
longest_page = ("", 0)
subdomains = {}
unique_urls = set()
def scraper(url, resp):
    global longest_page, subdomains

    actual_url = resp.url

    if resp.status != 200 or not resp.raw_response:
        return []

    if actual_url in unique_urls:
        return []

    unique_urls.add(actual_url)

    soup = BeautifulSoup(resp.raw_response.content, "html.parser")

    text = soup.get_text()
    words = re.findall(r"\w+", text.lower())

    for w in words:
        word_counts[w] = word_counts.get(w, 0) + 1

    # longest page
    if len(words) > longest_page[1]:
        longest_page = (actual_url, len(words))

    # subdomain counting
    parsed = urlparse(actual_url)
    hostname = parsed.hostname
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
        full_url = urljoin(resp.url, link['href'])
        # remove anything after '#'
        clean_url = full_url.split('#')[0]
        found_links.append(clean_url)

    return found_links


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if "?" in url:
            return False
        allowed_domains = [
            "ics.uci.edu",
            "cs.uci.edu",
            "informatics.uci.edu",
            "stat.uci.edu"
        ]

        if not (parsed.hostname and parsed.hostname.endswith(tuple(allowed_domains))):
            return False
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
