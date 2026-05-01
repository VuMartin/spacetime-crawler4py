import multiprocessing
multiprocessing.set_start_method("fork", force=True)

from configparser import ConfigParser
from argparse import ArgumentParser

from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler

def main(config_file, restart):
    cparser = ConfigParser()
    cparser.read(config_file)
    config = Config(cparser)
    config.cache_server = get_cache_server(config, restart)
    crawler = Crawler(config, restart)
    crawler.start()

    from scraper import word_counts, unique_urls, longest_page, subdomains

    with open("report.txt", "w") as f:
        # 1. Unique pages
        f.write(f"Unique pages: {len(unique_urls)}\n\n")

        # 2. Longest page
        f.write(f"Longest page: {longest_page[0]} ({longest_page[1]} words)\n\n")

        # 3. Top 50 words
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:50]
        f.write("Top 50 words:\n")
        for word, freq in sorted_words:
            f.write(f"{word} {freq}\n")

        # 4. Subdomains
        sorted_subs = sorted(subdomains.items())
        f.write("\nSubdomains:\n")
        for sub, count in sorted_subs:
            f.write(f"{sub}, {count}\n")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)
