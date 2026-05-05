import os
import textwrap


def strip_code_fence(text):
    lines = text.strip().splitlines()

    if len(lines) >= 2:
        if lines[0].strip().startswith("```") and lines[-1].strip().startswith("```"):
            return "\n".join(lines[1:-1]).strip()

    return text


def format_note(text, width=80):
    text = strip_code_fence(text)
    text = text.replace("\t", "   ")  # replace tab with 3 spaces

    lines = text.splitlines()
    out = []

    for line in lines:
        if not line.strip():
            out.append("")
            continue

        indent = len(line) - len(line.lstrip(" "))
        prefix = " " * indent
        stripped = line.lstrip(" ")

        bullet = ""
        if stripped.startswith("- "):
            bullet = "- "
            stripped = stripped[2:]

        elif stripped.startswith("* "):
            bullet = "* "
            stripped = stripped[2:]

        wrap_width = width - indent - len(bullet)

        wrapped = textwrap.wrap(
            stripped,
            width=wrap_width,
            break_long_words=False,
            replace_whitespace=False
        )

        if not wrapped:
            out.append(prefix + bullet)
        else:
            out.append(prefix + bullet + wrapped[0])

            hanging_indent = " " * (indent + len(bullet))

            for w in wrapped[1:]:
                out.append(hanging_indent + w)

    return "\n".join(out)


def shorten_path(path, keep_dirs=2):
    parts = os.path.normpath(path).split(os.sep)

    if len(parts) <= keep_dirs + 1:
        return path

    return os.sep.join(["...", *parts[-(keep_dirs + 1):]])


def render_note(note, width=80):
    short_path = shorten_path(note.file)
    header = f"{short_path} [{note.index}] line {note.line}"
    body = format_note(note.content, width=width)

    lines = body.splitlines()

    print(header)
    print("┌─")
    for line in lines:
        print(f"│ {line}")
    print("└─")
    print()


if __name__ == "__main__":
    import sys
    text = sys.stdin.read()
    print(format_note(text))
