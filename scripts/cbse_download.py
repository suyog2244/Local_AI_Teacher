#!/usr/bin/env python3

import re
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import urljoin
import html


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://ncert.nic.in/"
TEXTBOOK_PAGE = "https://ncert.nic.in/textbook.php"

OUTPUT_DIR = Path("books/ncert")

HTML_FILE = Path("/tmp/ncert_textbook.html")

START_CLASS = 1
END_CLASS = 12

USER_AGENT = "Mozilla/5.0"


# ============================================================
# HELPERS
# ============================================================

def sanitize_name(name: str) -> str:
    """
    Convert a book/subject name into a filesystem-safe directory name.
    """

    name = html.unescape(name)

    name = name.strip()

    name = re.sub(r"[<>:\"/\\|?*]", "", name)

    name = re.sub(r"\s+", "_", name)

    name = re.sub(r"_+", "_", name)

    return name.strip("_")


def run_command(command):
    """
    Run a command and return its exit code.
    """

    result = subprocess.run(command)

    return result.returncode


# ============================================================
# DOWNLOAD MAIN NCERT PAGE
# ============================================================

def download_ncert_page():
    """
    Download NCERT textbook.php.

    We use curl instead of Python requests because NCERT can
    sometimes reset Python HTTPS connections.
    """

    print()
    print("=" * 70)
    print("Downloading NCERT textbook page")
    print("=" * 70)

    command = [
        "curl",
        "--http1.1",
        "--location",
        "--retry", "5",
        "--retry-delay", "2",
        "--retry-all-errors",
        "--silent",
        "--show-error",
        "-A", USER_AGENT,
        "-o", str(HTML_FILE),
        TEXTBOOK_PAGE,
    ]

    result = subprocess.run(command)

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to download NCERT textbook page. "
            f"curl exit code: {result.returncode}"
        )

    if not HTML_FILE.exists():
        raise RuntimeError("NCERT HTML file was not created.")

    print(f"Saved: {HTML_FILE}")

    return HTML_FILE.read_text(
        encoding="utf-8",
        errors="ignore"
    )


# ============================================================
# PARSE CLASS INFORMATION
# ============================================================

def extract_class_subjects(content):
    """
    Parse the JavaScript change() function.

    Example:

        else if (document.test.tclass.value==1)
        {
            document.test.tsubject.options[1].text="English";
            document.test.tsubject.options[2].text="Mathematics";
        }

    Returns:

        {
            1: ["English", "Mathematics", "Hindi", "Urdu"],
            ...
        }
    """

    classes = {}

    # Find each class block.
    class_pattern = re.compile(
        r"document\.test\.tclass\.value\s*==\s*(\d+)"
        r"(.*?)(?="
        r"else\s+if\s*\(\s*document\.test\.tclass\.value"
        r"|function\s+change1"
        r")",
        re.DOTALL
    )

    for match in class_pattern.finditer(content):

        class_number = int(match.group(1))
        block = match.group(2)

        subjects = []

        subject_pattern = re.compile(
            r'document\.test\.tsubject\.options\[\d+\]\.text\s*=\s*"([^"]+)"'
        )

        for subject_match in subject_pattern.finditer(block):

            subject = subject_match.group(1).strip()

            if subject and subject not in subjects:
                subjects.append(subject)

        if subjects:
            classes[class_number] = subjects

    return classes


# ============================================================
# PARSE BOOK MAPPINGS
# ============================================================

def extract_books(content):
    """
    Parse the JavaScript change1() function.

    Returns a list containing:

        class
        subject
        book
        textbook URL
        textbook code
        range
    """

    books = []

    # Locate change1()
    start = content.find("function change1")

    if start == -1:
        raise RuntimeError("Could not find function change1().")

    block = content[start:]

    # --------------------------------------------------------
    # Find every class + subject condition
    # --------------------------------------------------------

    condition_pattern = re.compile(
        r'if\s*\(\s*'
        r'\(document\.test\.tclass\.value\s*==\s*(\d+)\)'
        r'\s*&&\s*'
        r'\(document\.test\.tsubject\.options\[sind\]\.text\s*==\s*"([^"]+)"\)'
        r'\s*\)'
        r'\s*\{'
        r'(.*?)(?=\n\s*\}\s*else\s+if|\n\s*\}\s*else|\n\s*\}\s*$)',
        re.DOTALL
    )

    for match in condition_pattern.finditer(block):

        class_number = int(match.group(1))

        subject = match.group(2).strip()

        section = match.group(3)

        # ----------------------------------------------------
        # Extract book title + value
        # ----------------------------------------------------

        book_pattern = re.compile(
            r'document\.test\.tbook\.options\[(\d+)\]\.text\s*=\s*"([^"]+)"'
            r'\s*;?\s*'
            r'document\.test\.tbook\.options\[\1\]\.value\s*=\s*"([^"]+)"',
            re.DOTALL
        )

        for book_match in book_pattern.finditer(section):

            option_index = int(book_match.group(1))

            book_name = book_match.group(2).strip()

            textbook_value = book_match.group(3).strip()

            # Skip the placeholder
            if option_index == 0:
                continue

            # ------------------------------------------------
            # Extract query parameter
            #
            # textbook.php?aemr1=0-9
            # ------------------------------------------------

            code_match = re.search(
                r'textbook\.php\?([a-zA-Z0-9]+)=([0-9]+)-([0-9]+)',
                textbook_value
            )

            if not code_match:
                continue

            code = code_match.group(1)

            start_page = code_match.group(2)

            end_page = code_match.group(3)

            # ------------------------------------------------
            # Construct ZIP URL
            #
            # aemr1 -> aemr1dd.zip
            # ------------------------------------------------

            zip_url = (
                f"https://ncert.nic.in/textbook/pdf/"
                f"{code}dd.zip"
            )

            books.append(
                {
                    "class": class_number,
                    "subject": subject,
                    "book": book_name,
                    "code": code,
                    "start": start_page,
                    "end": end_page,
                    "textbook_url": urljoin(
                        BASE_URL,
                        textbook_value
                    ),
                    "zip_url": zip_url,
                }
            )

    return books


# ============================================================
# ZIP VALIDATION
# ============================================================

def is_valid_zip(path: Path) -> bool:
    """
    Validate the ZIP.

    This is important because NCERT can sometimes return
    curl exit code 35 after the complete file has already
    been downloaded.
    """

    if not path.exists():
        return False

    if path.stat().st_size == 0:
        return False

    try:

        with zipfile.ZipFile(path, "r") as z:

            bad_file = z.testzip()

            if bad_file is not None:

                print(
                    f"    Corrupt file inside ZIP: {bad_file}"
                )

                return False

        return True

    except zipfile.BadZipFile:

        return False


# ============================================================
# DOWNLOAD ONE ZIP
# ============================================================

def download_zip(book):
    """
    Download one NCERT ZIP.
    """

    class_number = book["class"]

    subject = book["subject"]

    book_name = book["book"]

    zip_url = book["zip_url"]

    subject_dir = (
        OUTPUT_DIR
        / f"class_{class_number}"
        / sanitize_name(subject)
    )

    book_dir = subject_dir / sanitize_name(book_name)

    book_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    zip_file = book_dir / f"{book['code']}dd.zip"

    print()
    print("-" * 70)

    print(
        f"Class {class_number} | "
        f"{subject} | "
        f"{book_name}"
    )

    print(zip_url)

    # --------------------------------------------------------
    # Already downloaded?
    # --------------------------------------------------------

    if is_valid_zip(zip_file):

        print(
            f"Already downloaded and valid:"
            f" {zip_file}"
        )

        return True

    # --------------------------------------------------------
    # Temporary file
    # --------------------------------------------------------

    temp_file = zip_file.with_suffix(".download")

    if temp_file.exists():
        temp_file.unlink()

    # --------------------------------------------------------
    # Curl
    # --------------------------------------------------------

    command = [
        "curl",

        "--http1.1",

        "--location",

        "--retry", "10",

        "--retry-delay", "3",

        "--retry-all-errors",

        "--show-error",

        "--progress-bar",

        "-A", USER_AGENT,

        "-e",
        book["textbook_url"],

        "-o",
        str(temp_file),

        zip_url,
    ]

    result = subprocess.run(command)

    # --------------------------------------------------------
    # Check the file even when curl fails.
    # --------------------------------------------------------

    if temp_file.exists():

        size = temp_file.stat().st_size

        print(
            f"\nDownloaded size: "
            f"{size:,} bytes"
        )

        if is_valid_zip(temp_file):

            print(
                "ZIP validation successful."
            )

            temp_file.replace(zip_file)

            return True

    print(
        f"curl exit code: {result.returncode}"
    )

    print(
        "Download failed or ZIP is incomplete."
    )

    if temp_file.exists():
        temp_file.unlink()

    return False


# ============================================================
# EXTRACT ONE ZIP
# ============================================================

def extract_zip(book):
    """
    Extract PDFs from ZIP.
    """

    class_number = book["class"]

    subject = book["subject"]

    book_name = book["book"]

    book_dir = (
        OUTPUT_DIR
        / f"class_{class_number}"
        / sanitize_name(subject)
        / sanitize_name(book_name)
    )

    zip_file = (
        book_dir
        / f"{book['code']}dd.zip"
    )

    extract_dir = book_dir / "pdf"

    if not zip_file.exists():
        print(
            "ZIP does not exist. Skipping extraction."
        )

        return False

    if not is_valid_zip(zip_file):

        print(
            "ZIP is invalid. Skipping extraction."
        )

        return False

    extract_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    try:

        with zipfile.ZipFile(
            zip_file,
            "r"
        ) as z:

            pdf_files = [
                name
                for name in z.namelist()
                if name.lower().endswith(".pdf")
            ]

            for pdf in pdf_files:

                target = extract_dir / Path(pdf).name

                # --------------------------------------------
                # Don't extract again
                # --------------------------------------------

                if target.exists():
                    continue

                z.extract(
                    pdf,
                    extract_dir
                )

                # --------------------------------------------
                # ZIP may contain nested path.
                # Move PDF to flat directory.
                # --------------------------------------------

                extracted = extract_dir / pdf

                if extracted != target:

                    target.parent.mkdir(
                        parents=True,
                        exist_ok=True
                    )

                    extracted.replace(target)

        print(
            f"Extracted {len(pdf_files)} PDF(s)"
        )

        return True

    except Exception as e:

        print(
            f"Extraction failed: {e}"
        )

        return False


# ============================================================
# SAVE CATALOG
# ============================================================

def save_catalog(books):
    """
    Save all discovered NCERT books to a CSV-like text file.
    """

    catalog = OUTPUT_DIR / "catalog.tsv"

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with catalog.open(
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "class\tsubject\tbook\tcode\t"
            "start\tend\tzip_url\n"
        )

        for book in books:

            f.write(
                f"{book['class']}\t"
                f"{book['subject']}\t"
                f"{book['book']}\t"
                f"{book['code']}\t"
                f"{book['start']}\t"
                f"{book['end']}\t"
                f"{book['zip_url']}\n"
            )

    print()
    print(
        f"Catalog saved to: {catalog}"
    )


# ============================================================
# PRINT DISCOVERED BOOKS
# ============================================================

def print_books(books):
    """
    Print discovered books.
    """

    print()
    print("=" * 70)
    print("NCERT BOOKS DISCOVERED")
    print("=" * 70)

    current_class = None

    for book in books:

        if book["class"] != current_class:

            current_class = book["class"]

            print()
            print(
                f"CLASS {current_class}"
            )

        print(
            f"  {book['subject']:<35} "
            f"{book['book']:<40} "
            f"{book['code']}"
        )

    print()
    print(
        f"Total books discovered: {len(books)}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("NCERT TEXTBOOK DOWNLOADER")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Download NCERT page
    # --------------------------------------------------------

    content = download_ncert_page()

    # --------------------------------------------------------
    # 2. Parse classes/subjects
    # --------------------------------------------------------

    classes = extract_class_subjects(content)

    print()
    print(
        f"Classes with subjects found: "
        f"{len(classes)}"
    )

    # --------------------------------------------------------
    # 3. Parse books
    # --------------------------------------------------------

    books = extract_books(content)

    # Only Class 1-12
    books = [
        book
        for book in books
        if START_CLASS
        <= book["class"]
        <= END_CLASS
    ]

    # --------------------------------------------------------
    # 4. Remove duplicates
    # --------------------------------------------------------

    unique_books = {}

    for book in books:

        key = (
            book["class"],
            book["subject"],
            book["book"],
            book["code"],
        )

        unique_books[key] = book

    books = list(unique_books.values())

    # --------------------------------------------------------
    # 5. Sort
    # --------------------------------------------------------

    books.sort(
        key=lambda x: (
            x["class"],
            x["subject"],
            x["book"],
        )
    )

    # --------------------------------------------------------
    # 6. Print catalog
    # --------------------------------------------------------

    print_books(books)

    # --------------------------------------------------------
    # 7. Save catalog
    # --------------------------------------------------------

    save_catalog(books)

    # --------------------------------------------------------
    # 8. Download
    # --------------------------------------------------------

    successful = 0

    failed = 0

    print()
    print("=" * 70)
    print("DOWNLOADING BOOKS")
    print("=" * 70)

    for index, book in enumerate(
        books,
        start=1
    ):

        print()
        print(
            f"[{index}/{len(books)}]"
        )

        try:

            if download_zip(book):

                successful += 1

                extract_zip(book)

            else:

                failed += 1

        except KeyboardInterrupt:

            print()
            print(
                "Download interrupted by user."
            )

            break

        except Exception as e:

            failed += 1

            print(
                f"ERROR: {e}"
            )

    # --------------------------------------------------------
    # 9. Summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)

    print(
        f"Total books: {len(books)}"
    )

    print(
        f"Successful: {successful}"
    )

    print(
        f"Failed: {failed}"
    )

    print(
        f"Output directory: {OUTPUT_DIR}"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()