#!/usr/bin/env python3
"""
Anki .apkg Tool — Load, inspect, and save Anki decks using the official Anki library.

Usage:
    python3 anki_tool.py <file.apkg> [command]

Commands:
    summary     Overview of the deck (default)
    decks       List all decks
    models      Show note types and templates in detail
    notes       List all notes (can be large)
    save        Re-export to a new .apkg file
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from anki.collection import Collection
from anki.import_export_pb2 import ImportAnkiPackageRequest, ExportAnkiPackageOptions


class AnkiTool:
    """Load and manipulate Anki .apkg files using the official library."""

    def __init__(self):
        self.col = None
        self.tmp_dir = None
        self.source_path = None

    def load(self, apkg_path: str):
        """Import an .apkg file into a temporary collection."""
        self.source_path = Path(apkg_path).resolve()
        if not self.source_path.exists():
            raise FileNotFoundError(f"File not found: {apkg_path}")

        self.tmp_dir = tempfile.mkdtemp(prefix="anki_tool_")
        col_path = os.path.join(self.tmp_dir, "collection.anki2")

        self.col = Collection(col_path)
        request = ImportAnkiPackageRequest(package_path=str(self.source_path))
        self.col.import_anki_package(request)

    def save(self, output_path: str):
        """Export the collection to a new .apkg file."""
        if not self.col:
            raise RuntimeError("No collection loaded. Call load() first.")

        output = Path(output_path).resolve()
        self.col.export_anki_package(
            out_path=str(output),
            limit=None,
            with_scheduling=True,
            with_media=True,
        )
        print(f"✅ Saved to: {output}")

    def close(self):
        """Close the collection and clean up."""
        if self.col:
            self.col.close()
            self.col = None
        if self.tmp_dir and os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)
            self.tmp_dir = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ===== Query Methods =====

    def note_count(self) -> int:
        return self.col.note_count()

    def card_count(self) -> int:
        return self.col.card_count()

    def get_decks(self) -> list:
        """List all decks with names and IDs."""
        return [
            {"id": d.id, "name": d.name}
            for d in self.col.decks.all_names_and_ids()
        ]

    def get_models(self) -> list:
        """Get all note types with fields and templates."""
        results = []
        for m in self.col.models.all_names_and_ids():
            model = self.col.models.get(m.id)
            fields = [f["name"] for f in model["flds"]]
            templates = []
            for tmpl in model["tmpls"]:
                templates.append({
                    "name": tmpl["name"],
                    "front": tmpl["qfmt"],
                    "back": tmpl["afmt"],
                })
            results.append({
                "id": m.id,
                "name": m.name,
                "fields": fields,
                "templates": templates,
                "css": model.get("css", ""),
            })
        return results

    def get_notes(self, limit: int = None, deck: str = None) -> list:
        """Get notes, optionally filtered by deck name."""
        if deck:
            query = f'"deck:{deck}"'
        else:
            query = ""
        nids = self.col.find_notes(query)
        if limit:
            nids = nids[:limit]

        notes = []
        for nid in nids:
            note = self.col.get_note(nid)
            model = note.note_type()
            notes.append({
                "id": nid,
                "model_name": model["name"],
                "fields": dict(zip(
                    [f["name"] for f in model["flds"]],
                    note.fields
                )),
                "tags": note.tags,
            })
        return notes

    def get_card_stats(self) -> dict:
        """Get card status distribution."""
        cards = self.col.find_cards("")
        stats = {"new": 0, "learning": 0, "review": 0, "total": len(cards)}
        for cid in cards:
            card = self.col.get_card(cid)
            if card.type == 0:
                stats["new"] += 1
            elif card.type == 1:
                stats["learning"] += 1
            elif card.type == 2:
                stats["review"] += 1
        return stats

    # ===== Display Methods =====

    def print_summary(self):
        """Print a comprehensive summary of the loaded deck."""
        print("=" * 60)
        print(f"📦 APKG: {self.source_path.name}")
        print("=" * 60)

        # Counts
        n_notes = self.note_count()
        n_cards = self.card_count()
        print(f"\n📊 Statistics:")
        print(f"   Notes: {n_notes}")
        print(f"   Cards: {n_cards}")

        # Card status
        stats = self.get_card_stats()
        print(f"\n📈 Card Status:")
        print(f"   New:      {stats['new']}")
        print(f"   Learning: {stats['learning']}")
        print(f"   Review:   {stats['review']}")

        # Decks
        decks = self.get_decks()
        # Group by top-level
        top_decks = {}
        for d in decks:
            top = d["name"].split("::")[0]
            if top not in top_decks:
                top_decks[top] = []
            top_decks[top].append(d["name"])

        print(f"\n📚 Decks ({len(decks)} total, {len(top_decks)} top-level):")
        for top, children in sorted(top_decks.items()):
            if len(children) == 1:
                print(f"   • {top}")
            else:
                print(f"   • {top} ({len(children)} sub-decks)")

        # Models
        models = self.get_models()
        print(f"\n🎴 Note Types ({len(models)}):")
        for model in models:
            # Count notes using this model
            print(f"   • {model['name']}")
            print(f"     Fields: {', '.join(model['fields'])}")
            print(f"     Templates: {', '.join(t['name'] for t in model['templates'])}")

        # Sample notes
        notes = self.get_notes(limit=5)
        if notes:
            print(f"\n📝 Sample Notes (first 5 of {n_notes}):")
            for note in notes:
                print(f"\n   [{note['model_name']}]")
                for field_name, value in note["fields"].items():
                    val_clean = value.replace("\n", " ")[:80]
                    if val_clean:
                        print(f"     {field_name}: {val_clean}")
                if note["tags"]:
                    print(f"     Tags: {', '.join(note['tags'])}")

        print("\n" + "=" * 60)

    def print_decks(self):
        """Print all decks in tree structure."""
        decks = self.get_decks()
        print(f"📚 All Decks ({len(decks)}):\n")
        for d in sorted(decks, key=lambda x: x["name"]):
            depth = d["name"].count("::")
            indent = "  " * depth
            name = d["name"].split("::")[-1]
            print(f"{indent}• {name} (id: {d['id']})")

    def print_models(self):
        """Print detailed note type / template information."""
        models = self.get_models()
        for model in models:
            print(f"\n{'='*60}")
            print(f"📋 Model: {model['name']} (id: {model['id']})")
            print(f"   Fields: {model['fields']}")
            for tmpl in model["templates"]:
                print(f"\n   Template: {tmpl['name']}")
                print(f"   {'─'*40}")
                print(f"   FRONT:")
                for line in tmpl["front"].split("\n"):
                    print(f"     {line}")
                print(f"   BACK:")
                for line in tmpl["back"].split("\n"):
                    print(f"     {line}")
            if model["css"]:
                print(f"\n   CSS:")
                for line in model["css"].split("\n")[:10]:
                    print(f"     {line}")
                if model["css"].count("\n") > 10:
                    print(f"     ... ({model['css'].count(chr(10))} lines total)")
            print()

    def print_notes(self, limit: int = None, deck: str = None):
        """Print all notes."""
        notes = self.get_notes(limit=limit, deck=deck)
        total = self.note_count()
        showing = len(notes)
        print(f"📝 Notes (showing {showing} of {total}):\n")
        for note in notes:
            print(f"  [{note['model_name']}] id={note['id']}")
            for field_name, value in note["fields"].items():
                val_clean = value.replace("\n", " ")[:100]
                if val_clean:
                    print(f"    {field_name}: {val_clean}")
            if note["tags"]:
                print(f"    Tags: {', '.join(note['tags'])}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="Anki .apkg Tool — Load, inspect, and save Anki decks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 anki_tool.py deck.apkg                  # Show summary
  python3 anki_tool.py deck.apkg summary          # Same as above
  python3 anki_tool.py deck.apkg decks            # List all decks
  python3 anki_tool.py deck.apkg models           # Show templates
  python3 anki_tool.py deck.apkg notes            # List all notes
  python3 anki_tool.py deck.apkg notes --limit 20 # First 20 notes
  python3 anki_tool.py deck.apkg notes --deck "Yuan's English::CEFR::A1"
  python3 anki_tool.py deck.apkg save output.apkg # Re-export
        """,
    )
    parser.add_argument("apkg", help="Path to .apkg file")
    parser.add_argument("command", nargs="?", default="summary",
                        choices=["summary", "decks", "models", "notes", "save"],
                        help="Command to execute (default: summary)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of notes to display")
    parser.add_argument("--deck", type=str, default=None,
                        help="Filter notes by deck name")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output path for save command")

    args = parser.parse_args()

    with AnkiTool() as tool:
        print(f"Loading {args.apkg}...")
        tool.load(args.apkg)
        print(f"Loaded successfully.\n")

        if args.command == "summary":
            tool.print_summary()
        elif args.command == "decks":
            tool.print_decks()
        elif args.command == "models":
            tool.print_models()
        elif args.command == "notes":
            tool.print_notes(limit=args.limit, deck=args.deck)
        elif args.command == "save":
            output = args.output or args.apkg.replace(".apkg", "_modified.apkg")
            tool.save(output)


if __name__ == "__main__":
    main()
