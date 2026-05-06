#!/usr/bin/env python3

import argparse
import os
import re
import subprocess
import sys

from config import load_config
from formatting import format_note
from formatting import render_note
from formatting import strip_code_fence
from note import Note


SECTION_PATTERN = r'\n---\n'


# -----------------------
# File handling
# -----------------------

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


# -----------------------
# Section parsing
# -----------------------

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


def load_notes_from_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    sections = split_sections_with_lines(text)

    notes = []
    for i, (section, line) in enumerate(sections):
        notes.append(Note(
            file=path,
            index=i,
            line=line,
            content=section.strip()
        ))

    return notes


# -----------------------
# Matching logic
# -----------------------

# Words in the filename will be included in the search text for each note
# section.
def match_section(note, args):

    filename = os.path.basename(note.file)
    search_text = f"{filename} {note.content}".lower()

    if args.all and not all(w.lower() in search_text for w in args.all):
        return False

    if args.any and not any(w.lower() in search_text for w in args.any):
        return False

    if args.not_words and any(w.lower() in search_text for w in args.not_words):
        return False

    if args.re and not re.search(args.re, section, re.MULTILINE | re.DOTALL):
        return False

    return True


# -----------------------
# Commands
# -----------------------

def cmd_search(args):
    results = []

    for base_path in args.search_paths:
        for file in iter_files(base_path, args.ext, args.exclude):
            try:
                notes = load_notes_from_file(file)
            except Exception:
                continue

            for note in notes:
                if match_section(note, args):
                    results.append(note)

    if args.fzf:
        run_fzf(results, print_only=args.print)
    else:
        print()
        for note in results:
            render_note(note)


def cmd_list(args):
    for base_path in args.search_paths:
        for file in iter_files(base_path, args.ext, args.exclude):
            try:
                sections = load_notes_from_file(file)
            except Exception:
                continue

            for i, (section, line) in enumerate(sections):
                preview = section.strip().split("\n")[0][:80]
                print(f"{file} [{i}] line {line} :: {preview}")


def cmd_view(args):
    if not os.path.isfile(args.file):
        print("view requires a single file", file=sys.stderr)
        sys.exit(1)

    sections = load_notes_from_file(args.file)

    if args.index < 0 or args.index >= len(sections):
        print("Invalid section index", file=sys.stderr)
        sys.exit(1)

    section, line = sections[args.index]
    print(f"{args.file} [{args.index}] line {line}\n")
    print(section.strip())

    if args.open:
        open_in_editor(args.file, line)


def cmd_stats(args):
    total_sections = 0
    total_lines = 0

    for base_path in args.search_paths:
        for file in iter_files(base_path, args.ext, args.exclude):
            try:
                sections = load_notes_from_file(file)
            except Exception:
                continue

        total_sections += len(sections)
        total_lines += sum(s.count("\n") for s, _ in sections)

    print(f"Sections: {total_sections}")
    print(f"Total lines (approx): {total_lines}")
    if total_sections:
        print(f"Avg section size: {total_lines // total_sections} lines")


# -----------------------
# Helpers
# -----------------------

def parse_header(header):
    file_part, rest = header.split(" [", 1)
    line = int(rest.split("line ")[1].strip())
    return file_part, line


def open_in_editor(file, line):
    import os
    import shlex
    import subprocess
    import sys

    editor_env = os.environ.get("EDITOR", "vim")
    cmd = shlex.split(editor_env)

    if not cmd:
        print("EDITOR is empty", file=sys.stderr)
        return

    try:
        if "code" in cmd[0]:
            # VS Code
            cmd.extend(["-g", f"{file}:{line}"])
        else:
            # vim / nvim / others
            cmd.extend([f"+{line}", file])

        subprocess.run(cmd)

    except FileNotFoundError:
        print(f"Editor not found: {cmd[0]}", file=sys.stderr)


def run_fzf(notes, print_only=False):
    import subprocess

    if not notes:
        return

    SEP = "\x1f"

    entries = []
    for n in notes:

        clean = strip_code_fence(n.content)
        preview = clean.split("\n")[0][:80]

        safe = n.content.replace("\t", "   ")
        encoded = safe.replace("\n", SEP)

        # preview | file | line | content
        entries.append(f"{preview}\t{n.file}\t{n.line}\t{encoded}")

    preview_cmd = f"echo {{4}} | tr '{SEP}' '\\n' | python formatting.py"

    proc = subprocess.Popen(
        [
            "fzf",
            "--with-nth=1",
            "--delimiter=\t",
            "--preview", preview_cmd,
            "--preview-window=up:70%:wrap"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )

    out, _ = proc.communicate("\n".join(entries))

    if not out:
        return

    parts = out.strip().split("\t", 3)
    if len(parts) < 3:
        return

    file = parts[1]
    line = int(parts[2])
    content = parts[3].replace(SEP, "\n")

    if print_only:
        note = Note(file=file, index=0, line=line, content=content)
        print()
        render_note(note)
    else:
        open_in_editor(file, line)


# -----------------------
# CLI setup
# -----------------------

def main():
    parser = argparse.ArgumentParser(prog="notes")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = subparsers.add_parser("search")
    p_search.add_argument("--path", nargs="+")
    p_search.add_argument("--all", nargs="+")
    p_search.add_argument("--any", nargs="+")
    p_search.add_argument("--not-words", nargs="+")
    p_search.add_argument("--re")
    p_search.add_argument("--fzf", action="store_true")
    p_search.add_argument("--print", action="store_true", help="print instead of opening from fzf")
    p_search.add_argument("--ext", nargs="+", help="e.g. .txt .md")
    p_search.add_argument("--exclude", nargs="+", help="skip paths containing these")
    p_search.set_defaults(func=cmd_search)

    # list
    p_list = subparsers.add_parser("list")
    p_list.add_argument("path")
    p_list.add_argument("--ext", nargs="+")
    p_list.add_argument("--exclude", nargs="+")
    p_list.set_defaults(func=cmd_list)

    # view
    p_view = subparsers.add_parser("view")
    p_view.add_argument("file")
    p_view.add_argument("index", type=int)
    p_view.add_argument("--open", action="store_true")
    p_view.set_defaults(func=cmd_view)

    # stats
    p_stats = subparsers.add_parser("stats")
    p_stats.add_argument("path")
    p_stats.add_argument("--ext", nargs="+")
    p_stats.add_argument("--exclude", nargs="+")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()

    config = load_config()

    if args.path:
        args.search_paths = args.path
    else:
        args.search_paths = config["search_paths"]
    
    args.width = config.get("width", 80);

    args.func(args)


if __name__ == "__main__":
    main()
