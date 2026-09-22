# DutchPiffAudioDownloader

## Requirements

* Python 3 (3.13)
* Playwright
* Chromium

## Installation

### Step 1

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Then install the Chromium browser used by Playwright:

```bash
playwright install chromium
```

### Step 2

Run the Python script and enter a valid DutchPiff album/mixtape URL when prompted.

### Step 3

A Chrome/Chromium browser window will open.

**DO NOT CLOSE THE BROWSER WINDOW.**

Press **Play** on Track 1 and let the downloader run through the mixtape.

The downloader will automatically download each track and the album cover.

Your mixtape will be saved inside the `downloads` folder created by the script.

## Example

```text
Paste DutchPiff album URL:
> https://dutchpiff.com/albums/album-986
```
