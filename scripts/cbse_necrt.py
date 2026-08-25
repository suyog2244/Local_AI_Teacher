import requests
from bs4 import BeautifulSoup

# wget -S https://ncert.nic.in/textbook.php -O /tmp/ncert.html


HTML_FILE = "/tmp/ncert.html"

with open(HTML_FILE, "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("TITLE:")
print(soup.title.get_text(strip=True))

print("\nFORMS:")
for form in soup.find_all("form"):
    print("=" * 60)
    print("action:", form.get("action"))
    print("method:", form.get("method"))

print("\nSELECT ELEMENTS:")
for select in soup.find_all("select"):
    print("=" * 60)
    print("name:", select.get("name"))
    print("id:", select.get("id"))

    for option in select.find_all("option"):
        print(
            f"  text={option.get_text(strip=True)!r}, " f"value={option.get('value')!r}"
        )
