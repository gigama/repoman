#!/usr/bin/env python3
"""
alpha.py - Verify GitHub repos and generate alphabetic markdown listings.

Combines repos.txt and cloned.txt into a single deduplicated, alphabetically
sorted listing (by repo and by user). Repos sourced from cloned.txt are
marked with a trailing ' *' on their listing line. If a repo appears in
both files, it is treated as cloned (marked).

Strips ANSI escape codes, handles CRLF in HTTP redirect headers, and uses
requests with timeouts for reliable verification.

Usage:
  alpha.py                        # verify both files, generate combined listings
  alpha.py --skip                 # skip verification, generate combined listings
"""

import argparse
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' library required. Install with: pip install requests")
    sys.exit(1)

BASE = Path(__file__).parent
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


def green(s):   return f"\033[1;32m{s}\033[m"
def magenta(s): return f"\033[1;35m{s}\033[m"
def cyan(s):    return f"\033[1;36m{s}\033[m"
def red(s):     return f"\033[1;31m{s}\033[m"


def strip_ansi(text):
    return ANSI_RE.sub('', text)


def load_repos(path):
    """Read a repo list file, stripping ANSI codes, whitespace, and bad lines."""
    repos = []
    try:
        with open(path) as f:
            for line in f:
                repo = strip_ansi(line).strip().lower()
                if repo and repo.count('/') == 1:
                    repos.append(repo)
    except FileNotFoundError:
        print(f"Warning: {path} not found")
    return repos


def verify_repos(repos):
    """HEAD-check each repo; follow 301 redirects to get the new name."""
    verified = []
    for repo in repos:
        url = f"https://github.com/{repo}"
        try:
            resp = requests.head(url, allow_redirects=False, timeout=15)
            code = resp.status_code

            if code == 200:
                print(green(f"  {url} = {code}"))
                verified.append(repo)
            elif code == 301:
                print(magenta(f"  {url} = {code}"))
                final = requests.head(url, allow_redirects=True, timeout=15)
                parts = final.url.rstrip('/').split('/')
                if len(parts) >= 2:
                    new_repo = f"{parts[-2]}/{parts[-1]}".lower()
                    print(cyan(f"  -> {new_repo}"))
                    verified.append(new_repo)
                else:
                    print(red(f"  Could not parse redirect: {final.url}"))
            else:
                print(red(f"  {url} = {code}"))

        except requests.RequestException as e:
            print(red(f"  Error {repo}: {e}"))

        time.sleep(1)

    return verified


def make_listings(repos, cloned_set):
    """Return (by_repo, by_user) sorted entry lists.

    Each entry is (sort_key, user, reponame, is_cloned).
    Repos in both review and cloned are treated as cloned.
    """
    by_repo, by_user = [], []
    seen = set()
    for repo in repos:
        if repo in seen:
            continue
        seen.add(repo)
        parts = repo.split('/', 1)
        if len(parts) != 2:
            continue
        user, reponame = parts
        is_cloned = repo in cloned_set
        by_repo.append((reponame, user, reponame, is_cloned))
        by_user.append((user, user, reponame, is_cloned))

    by_repo.sort(key=lambda x: x[0].lower())
    by_user.sort(key=lambda x: x[0].lower())
    return by_repo, by_user


def write_md(outpath, title, subtitle, entries):
    """Write markdown with alphabetic section headers. Cloned repos get a trailing ' *'."""
    lines = [f"# {title}", "", f"### {subtitle}"]
    last_letter = None
    for sort_key, user, reponame, is_cloned in entries:
        letter = sort_key[0].upper()
        if letter != last_letter:
            lines.append("")
            lines.append(f"## {letter}")
            last_letter = letter
        marker = " *" if is_cloned else ""
        lines.append(f"- [{user}/{reponame}](https://github.com/{user}/{reponame}){marker}")

    with open(outpath, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"  Written: {outpath.name} ({len(entries)} entries)")


def process(skip_verify):
    review_path = BASE / "review.txt"
    cloned_path = BASE / "cloned.txt"

    review_repos = load_repos(review_path)
    cloned_repos = load_repos(cloned_path)
    print(f"\nLoaded {len(review_repos)} repos from review.txt, "
          f"{len(cloned_repos)} repos from cloned.txt")

    if not skip_verify:
        for path in (review_path, cloned_path):
            if path.exists():
                backup = BASE / f"{path.stem}-backup.txt"
                shutil.copy(path, backup)
                print(f"  Backed up {path.name} to {backup.name}")

        # Verify each source file's repos independently (rather than as one
        # merged batch) so redirects can be mapped back to the correct file
        # and review.txt/cloned.txt each accurately reflect their own results.
        if review_repos:
            print(f"  Verifying {len(review_repos)} repos from review.txt...")
            review_repos = verify_repos(review_repos)
        if cloned_repos:
            print(f"  Verifying {len(cloned_repos)} repos from cloned.txt...")
            cloned_repos = verify_repos(cloned_repos)

        with open(review_path, 'w') as f:
            f.write('\n'.join(review_repos) + '\n')
        with open(cloned_path, 'w') as f:
            f.write('\n'.join(cloned_repos) + '\n')

        print(f"  {len(review_repos)} repos remain in review.txt after verification")
        print(f"  {len(cloned_repos)} repos remain in cloned.txt after verification")

    combined = review_repos + cloned_repos

    cloned_set = set(cloned_repos)
    by_repo, by_user = make_listings(combined, cloned_set)
    write_md(BASE / "repos-by-repo.md", "repos", "by repo", by_repo)
    write_md(BASE / "repos-by-user.md", "repos", "by user", by_user)


def main():
    parser = argparse.ArgumentParser(
        description='Verify GitHub repos and generate combined sorted markdown listings.'
    )
    parser.add_argument('--skip', action='store_true', help='Skip URL verification')
    args = parser.parse_args()

    process(args.skip)


if __name__ == '__main__':
    main()
