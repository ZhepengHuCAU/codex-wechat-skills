# Publishing Package Standard

## Inputs

- Latest DOCX or final manuscript.
- Ordered final-resolution PNG/JPEG cards, either embedded in the DOCX or supplied separately.
- Final or proposed title, author, digest, original URL, source list, and data vintage.
- Optional horizontal and square covers.

## Package Contract

- Never silently overwrite an existing release folder. Create a versioned output or require an explicit force flag.
- Preserve a copy of the exact source document used.
- Number images in reading order. Use short conclusion-based filenames rather than generic `image1.png` when known.
- Store structured metadata in UTF-8 JSON and human-readable metadata in UTF-8 text.
- Record SHA-256, byte size, and image dimensions in `manifest.json`.
- Create a ZIP with one top-level package directory.

## Publication Metadata

- Title: preferably under 30 Chinese characters when possible, with the central tension or result.
- Digest: one or two sentences, generally 80–120 Chinese characters. State what happened and why it matters; do not simply repeat the headline.
- Author: default to the supplied institutional author.
- Alternative titles: provide two materially different angles, not punctuation variants.
- Cover: state whether supplied, generated, suggested, or omitted.

## Manual Import Note

Local HTML images often do not survive browser copy/paste because the WeChat editor cannot access `file://` paths. The package must therefore keep a numbered `images/` folder and tell the user to upload those images in order if they do not appear after pasting.