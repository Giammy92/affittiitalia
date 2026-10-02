"""Refresh the site when the Agenzia delle Entrate publishes a new OMI semester.

Reads the newest semester offered by the public consultation service and compares it with
site/data/index.json. If newer: fetches that semester and the same semester two years
earlier (for the trend), then rebuilds map data, city pages and the preview image.

Exit code 0 always; prints NEW_SEMESTER=<code> (or NO_CHANGE) for the workflow to read.

Usage: python scripts/refresh.py [--force]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import fetch_values as fv

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent


def latest_semester():
    fv.session.get(fv.BASE + "ricerca.htm", timeout=60)
    html = fv.post("ricerca.php", {"level": "1", "lingua": "IT", "pr": "MI"})
    sems = re.findall(r'<option value="(\d{5})"', html)
    return max(sems)


def run(*args):
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main():
    index = json.loads((ROOT / "site/data/index.json").read_text(encoding="utf-8"))
    current = index["semestre"].replace("-S", "")
    latest = latest_semester()
    print(f"current={current} latest={latest}")
    if latest <= current and "--force" not in sys.argv:
        print("NO_CHANGE")
        return
    compare = f"{int(latest[:4]) - 2}{latest[4]}"
    run(str(SCRIPTS / "fetch_values.py"), latest)
    run(str(SCRIPTS / "fetch_values.py"), compare)
    run(str(SCRIPTS / "build_data.py"), latest, compare)
    run(str(SCRIPTS / "build_pages.py"))
    run(str(SCRIPTS / "make_og.py"))
    print(f"NEW_SEMESTER={latest}")


if __name__ == "__main__":
    main()
