"""Download the public policy PDFs into data/raw (used at Docker build time).
Run:  python scripts/download_pdfs.py
"""
import os
import sys
import urllib.parse
import urllib.request
 
URLS = [
    "https://www.universalsompo.com/assets/file/a-plus-health-insurance/a-plus-health-insurance-policy-wording.pdf",
    "https://www.iffcotokio.co.in/content/dam/iffcotokio/iffco-pdf/sites/default/files/pdf/Health%20Protector%20Policy%20Wording.pdf",
    "https://uiic.co.in/web/sites/default/files/Policy-Document/20240325_Prospectus_IHIP.pdf",
    "https://www.eindiainsurance.com/brochure/religare-health-care-advantage-policy-wordings.pdf",
]
OUT = os.path.join("data", "raw")
os.makedirs(OUT, exist_ok=True)
 
ok = 0
for url in URLS:
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    path = os.path.join(OUT, name)
    if os.path.exists(path):
        print("have", name)
        ok += 1
        continue
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
            f.write(r.read())
        print("downloaded", name)
        ok += 1
    except (OSError,ValueError) as e:
        print("FAILED", name, "->", e)
 
if ok == 0:
    sys.exit("No PDFs available; check the URLs.")
 