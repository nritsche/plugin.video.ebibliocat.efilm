"""Kodi plugin entry point. Never log plugin arguments or resolved URLs."""

import sys
from urllib.parse import parse_qs

from resources.lib.ui.UI import UI


def main(argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) < 3:
        raise ValueError("Run this add-on through Kodi")
    try:
        arguments = parse_qs(argv[2].lstrip("?"), keep_blank_values=True, max_num_fields=20)
    except ValueError:
        arguments = {"mode": ["invalid"]}
    UI(argv[0], int(argv[1]), arguments).run()


if __name__ == "__main__":
    main()
