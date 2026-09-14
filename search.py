import os
import re

from note import Note


SECTION_PATTERN = r'\n---\n'


def iter_files(path, exts=None, exclude=None):
    if os.path.isfile(path):
        yield path
        return

    for root, _, files in os.walk(path):
        for name in files:
            full = os.path.join(root, name)

            if exclude and any(e in full for e in exclude):
                continue

            if exts and not any(name.endswith(e) for e in exts):
                continue

            yield full


def split_sections_with_lines(text):
    sections = []
    start = 0
    line_num = 1

    for match in re.finditer(SECTION_PATTERN, text):
        end = match.start()
        section = text[start:end]
        sections.append((section, line_num))

        line_num += section.count("\n") + match.group().count("\n")
        start = match.end()

    section = text[start:]
    sections.append((section, line_num))

    return sections


def get_note_title(section, file):
    # Prefer a ## heading at the beginning of the section.
    match = re.match(r'^\s*##\s+(.+?)\s*$', section, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Otherwise use the first non-empty line.
    for line in section.splitlines():
        line = line.strip()
        if line:
            return line

    # Empty section: fall back to filename.
    return os.path.basename(file)


def load_notes_from_file(path, collection_name):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    sections = split_sections_with_lines(text)

    notes = []
    for index, (section, line) in enumerate(sections):
        content = section.strip()

        notes.append(Note(
            collection=collection_name,
            file=path,
            index=index,
            line=line,
            title=get_note_title(content, path),
            content=content
        ))

    return notes


def get_collection_paths(config, collection_name):
    collections = config.get("collections", {})

    if collection_name not in collections:
        available = ", ".join(collections)

        raise ValueError(
            f"Unknown collection '{collection_name}'. "
            f"Available collections: {available}"
        )

    collection = collections[collection_name]
    root = os.path.abspath(collection["path"])

    # No "include" means the entire collection.
    if "include" not in collection:
        return [root]

    paths = []

    for relative_path in collection["include"]:
        path = os.path.abspath(os.path.join(root, relative_path))

        # Don't allow an include path to escape the collection root.
        if os.path.commonpath([root, path]) != root:
            raise ValueError(
                f"Collection path escapes root: {relative_path}"
            )

        paths.append(path)

    return paths


def get_search_paths(config, collection_names=None):
    collections = config.get("collections", {})

    if collection_names is None:
        collection_names = collections.keys()

    paths = []

    for collection_name in collection_names:
        for path in get_collection_paths(config, collection_name):
            paths.append((collection_name, path))

    return paths


# Words in the filename will be included in the search text for each note
# section.
def match_section(note, args):

    filename = os.path.basename(note.file)
    search_text = f"{filename} {note.content}".lower()

    if args.all and \
       not all(w.lower() in search_text for w in args.all):
        return False

    if args.any and \
       not any(w.lower() in search_text for w in args.any):
        return False

    if args.not_words and \
       any(w.lower() in search_text for w in args.not_words):
        return False

    if args.re and \
       not re.search(args.re, note.content, re.MULTILINE | re.DOTALL):
        return False

    return True


def search_notes(search_paths, ext=None, exclude=None,
                 all_words=None, any_words=None,
                 not_words=None, regex=None):

    results = []

    for collection_name, base_path in search_paths:
        for file in iter_files(base_path, ext, exclude):
            try:
                notes = load_notes_from_file(file, collection_name)
            except Exception:
                continue

            for note in notes:
                # Build an args-like object for the existing matcher.
                class Args:
                    pass

                args = Args()
                args.all = all_words
                args.any = any_words
                args.not_words = not_words
                args.re = regex

                if match_section(note, args):
                    results.append(note)

    return results
