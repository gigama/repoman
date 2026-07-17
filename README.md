# repoman

Github repos for review:

### repos
- [by user](https://github.com/gigama/repoman/blob/main/repos-by-user.md)
- [by repo](https://github.com/gigama/repoman/blob/main/repos-by-repo.md)

---

## list generator

`alpha.py` - Verify GitHub repos and generate alphabetic markdown listings.

Strips ANSI escape codes, handles CRLF in HTTP redirect headers, and uses 
requests with timeouts for reliable verification.

Usage:
```
alpha.py                        # verify review.txt, generate md files
alpha.py --skip                 # skip verification, generate md files
```
