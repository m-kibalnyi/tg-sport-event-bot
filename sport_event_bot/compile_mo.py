import os

import polib


def compile_po(po_path, mo_path):
    po = polib.pofile(po_path)
    po.save_as_mofile(mo_path)
    print(f"Compiled {po_path} -> {mo_path}")


locales = [("uk", "ua"), ("ru", "ru"), ("pl", "pl")]

for lang, domain in locales:
    po_file = f"sport_event_bot/locale/{lang}/LC_MESSAGES/{domain}.po"
    mo_file = f"sport_event_bot/locale/{lang}/LC_MESSAGES/{domain}.mo"
    if os.path.exists(po_file):
        compile_po(po_file, mo_file)
    else:
        print(f"Skipping {po_file} (not found)")
