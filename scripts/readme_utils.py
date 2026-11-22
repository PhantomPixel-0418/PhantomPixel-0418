"""Shared helpers for the README-update scripts.

Each dynamic section of README.md is wrapped in two HTML comments:

    <!--START_SECTION:<name>-->
    ```bash
    <content>
    ```
    <!--END_SECTION:<name>-->

The comment markers stay in the file; the fenced block between them is
replaced by update_section(). Because the markers are invisible HTML
comments, the rendered README keeps its clean terminal look.
"""

import re

README_PATH = "README.md"
FENCE = "bash"


def read_readme():
    """Return the current README.md content."""
    with open(README_PATH, encoding="utf-8") as handle:
        return handle.read()


def write_readme(text):
    """Write README.md with a final newline."""
    with open(README_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def replace_section(text, section, content, fence=FENCE):
    """Replace the body of a marker section with new content.

    The content is wrapped in a fenced code block unless fence is None,
    in which case it is inserted verbatim (used for plain-HTML sections
    like the right-aligned refresh date).
    """
    start = f"<!--START_SECTION:{section}-->"
    end = f"<!--END_SECTION:{section}-->"
    pattern = re.compile(re.escape(start) + r"[\s\S]+?" + re.escape(end))
    if not pattern.search(text):
        raise SystemExit(f"Markers for section '{section}' not found in {README_PATH}")
    if fence:
        replacement = f"{start}\n\n```{fence}\n{content}\n```\n\n{end}"
    else:
        replacement = f"{start}\n{content}\n{end}"
    # Lambda replacement inserts content verbatim, without re.sub processing
    # backslash escapes in it (a plain-string replacement would turn \\n into
    # a literal newline inside the fenced block).
    return pattern.sub(lambda m: replacement, text, count=1)


def update_section(section, content, fence=FENCE):
    """Replace a section in README.md, writing the file only if changed.

    A missing marker is reported but does not abort the run: the script
    exits 0 so the other sections still get updated and committed.
    Pass fence=None for plain-HTML sections that need no code fence.
    """
    text = read_readme()
    try:
        updated = replace_section(text, section, content, fence)
    except SystemExit as error:
        print(f"{error}, skipping section '{section}'")
        return False
    if updated == text:
        print(f"No changes for section '{section}'")
        return False
    write_readme(updated)
    print(f"Updated section '{section}'")
    return True