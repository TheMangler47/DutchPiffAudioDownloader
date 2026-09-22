import asyncio
import os
import re
from urllib.parse import urlparse, unquote

from playwright.async_api import async_playwright


DOWNLOAD_FOLDER = "downloads"


def clean_filename(name):
    name = unquote(name)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "track"


def extension_from_url(url):
    path = urlparse(url).path.lower()

    for ext in [".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg", ".opus"]:
        if ext in path:
            return ext

    return ".mp3"


def filename_from_url(url):
    path = unquote(urlparse(url).path)
    filename = os.path.basename(path)

    if filename:
        return clean_filename(filename)

    return None


async def download_cover(page, album_url, album_folder):
    match = re.search(r"album-(\d+)", album_url)

    if not match:
        print()
        print("Could not determine album ID.")
        print("Cover will not be downloaded.")
        return False

    album_id = match.group(1)

    cover_url = (
        f"https://dutchpiff.com/images/"
        f"album-{album_id}-cover.jpg"
    )

    output = os.path.join(
        album_folder,
        "cover.jpg"
    )

    print()
    print("=" * 70)
    print("DOWNLOADING COVER")
    print("=" * 70)

    print()
    print("Cover URL:")
    print(cover_url)

    try:
        response = await page.request.get(cover_url)

        if not response.ok:
            print()
            print(
                f"Cover download failed: "
                f"HTTP {response.status}"
            )
            return False

        data = await response.body()

        if not data:
            print()
            print("Cover response was empty.")
            return False

        with open(output, "wb") as f:
            f.write(data)

        print()
        print("✓ Cover saved:")
        print(output)

        print(
            f"  Size: {len(data) / 1024 / 1024:.2f} MB"
        )

        return True

    except Exception as e:
        print()
        print(f"Cover download error: {e}")
        return False


async def download_audio(page, url, output):
    print()
    print("Downloading:")
    print(url)

    try:
        response = await page.request.get(url)

        if not response.ok:
            print(
                f"Download failed: HTTP {response.status}"
            )
            return False

        data = await response.body()

        if not data:
            print("Empty response.")
            return False

        with open(output, "wb") as f:
            f.write(data)

        print(
            f"✓ Saved: {os.path.basename(output)}"
        )

        print(
            f"  Size: {len(data) / 1024 / 1024:.2f} MB"
        )

        return True

    except Exception as e:
        print(f"Download error: {e}")
        return False


async def get_audio_source(page):
    try:
        audio = page.locator("audio").first

        if await audio.count():
            source = await audio.evaluate(
                "el => el.currentSrc || el.src || ''"
            )

            if source:
                return source

    except Exception:
        pass

    return None


async def find_next_buttons(page):
    selectors = [
        "button",
        "[role='button']",
        "a",
        "[aria-label]",
        "[title]",
        "[data-testid]",
    ]

    results = []

    for selector in selectors:
        try:
            elements = page.locator(selector)
            count = await elements.count()

            for i in range(count):
                element = elements.nth(i)

                try:
                    if not await element.is_visible():
                        continue

                    text = ""

                    try:
                        text = await element.inner_text()
                    except Exception:
                        pass

                    aria = await element.get_attribute(
                        "aria-label"
                    )

                    title = await element.get_attribute(
                        "title"
                    )

                    testid = await element.get_attribute(
                        "data-testid"
                    )

                    combined = " ".join(
                        [
                            text or "",
                            aria or "",
                            title or "",
                            testid or "",
                        ]
                    ).lower()

                    if any(
                        word in combined
                        for word in [
                            "next",
                            "next track",
                            "forward",
                            "skip",
                            "volgende",
                        ]
                    ):
                        results.append(element)

                except Exception:
                    pass

        except Exception:
            pass

    return results


async def try_keyboard_next(page):
    keys = [
        "MediaTrackNext",
        "N",
    ]

    for key in keys:
        try:
            await page.keyboard.press(key)
            await page.wait_for_timeout(1500)
            return True
        except Exception:
            pass

    return False


async def download_album(page, album_url):
    print()
    print("=" * 70)
    print("DutchPiff Audio Downloader by TheMangler47")
    print("=" * 70)

    print()
    print("Opening:")
    print(album_url)

    await page.goto(
        album_url,
        wait_until="domcontentloaded",
        timeout=60000,
    )

    await page.wait_for_timeout(5000)

    print()
    print("Page loaded.")

    title = "DutchPiff Album"

    try:
        h1 = page.locator("h1").first

        if await h1.count():
            text = await h1.inner_text()

            if text.strip():
                title = clean_filename(text)

    except Exception:
        pass

    album_folder = os.path.join(
        DOWNLOAD_FOLDER,
        title
    )

    os.makedirs(
        album_folder,
        exist_ok=True
    )

    print()
    print("Album:", title)
    print("Folder:", album_folder)

    await download_cover(
        page,
        album_url,
        album_folder
    )

    print()
    print("Waiting for player...")

    audio_url = None

    for _ in range(20):
        audio_url = await get_audio_source(page)

        if audio_url:
            break

        await page.wait_for_timeout(500)

    if not audio_url:
        print()
        print("ERROR: No audio source found.")
        return

    print()
    print("First track:")
    print(audio_url)

    downloaded_urls = set()
    track_number = 1

    while True:
        audio_url = await get_audio_source(page)

        if not audio_url:
            print("No current audio source.")
            break

        if audio_url in downloaded_urls:
            print()
            print(
                "This track has already been downloaded."
            )

        else:
            print()
            print("=" * 70)
            print(f"TRACK {track_number}")
            print("=" * 70)

            print(audio_url)

            original_filename = filename_from_url(
                audio_url
            )

            if original_filename:
                filename = original_filename
            else:
                filename = f"{track_number:02d}.mp3"

            filename = clean_filename(filename)

            output = os.path.join(
                album_folder,
                filename
            )

            if os.path.exists(output):
                base, ext = os.path.splitext(
                    filename
                )

                counter = 2

                while os.path.exists(output):
                    filename = (
                        f"{base}_{counter}{ext}"
                    )

                    output = os.path.join(
                        album_folder,
                        filename
                    )

                    counter += 1

            success = await download_audio(
                page,
                audio_url,
                output
            )

            if success:
                downloaded_urls.add(audio_url)

        print()
        print("Looking for Next Track button...")

        next_buttons = await find_next_buttons(
            page
        )

        print(
            f"Possible next buttons: "
            f"{len(next_buttons)}"
        )

        old_url = audio_url
        changed = False

        for button in next_buttons:
            try:
                description = ""

                try:
                    description = await button.inner_text()
                except Exception:
                    pass

                print(
                    "Trying button:",
                    repr(description)
                )

                await button.click(
                    timeout=3000,
                    force=True
                )

                for _ in range(30):
                    await page.wait_for_timeout(300)

                    new_url = await get_audio_source(
                        page
                    )

                    if new_url and new_url != old_url:
                        changed = True

                        print()
                        print(
                            "Next track detected:"
                        )

                        print(new_url)

                        break

                if changed:
                    break

            except Exception:
                continue

        if not changed:
            print()
            print("Next button not found.")
            print("Trying keyboard control...")

            await try_keyboard_next(page)

            for _ in range(20):
                await page.wait_for_timeout(300)

                new_url = await get_audio_source(
                    page
                )

                if new_url and new_url != old_url:
                    changed = True

                    print()
                    print(
                        "Next track detected:"
                    )

                    print(new_url)

                    break

        if not changed:
            print()
            print("=" * 70)
            print("NO NEXT TRACK FOUND")
            print("=" * 70)
            break

        track_number += 1

        if track_number > 200:
            print("Safety limit reached.")
            break

    print()
    print("=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)

    print()
    print(
        "Tracks downloaded:",
        len(downloaded_urls)
    )

    print()
    print("Saved to:")
    print(os.path.abspath(album_folder))


async def main():
    os.makedirs(
        DOWNLOAD_FOLDER,
        exist_ok=True
    )

    print()
    print("=" * 70)
    print("DutchPiff Audio Downloader by TheMangler47")
    print("=" * 70)

    url = input(
        "\nPaste DutchPiff album URL:\n> "
    ).strip()

    if not url:
        print("No URL entered.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False
        )

        context = await browser.new_context(
            viewport={
                "width": 1400,
                "height": 900
            }
        )

        page = await context.new_page()

        try:
            await download_album(
                page,
                url
            )

            print()
            print(
                "Browser will close in 5 seconds...",
                "Thanks for using DutchPiff Audio Downloader by TheMangler47!"
            )

            await page.wait_for_timeout(5000)

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
