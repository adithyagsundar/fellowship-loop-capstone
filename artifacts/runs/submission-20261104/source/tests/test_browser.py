"""Run: python3 -m unittest discover -s tests -p 'test_*.py' -v

Build first: source ~/Developer/emsdk/emsdk_env.sh && bash build.sh
Requires Node >=22 and Chrome (CHROME_BIN can override its location).
Results, source/build hashes, browser logs and screenshots go to artifacts/.
"""
import os
from pathlib import Path
import subprocess
import unittest


class BrowserAcceptance(unittest.TestCase):
    def test_playable_browser_port(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["node", str(root / "tests/browser.mjs")], cwd=root,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=120, env=os.environ.copy(),
        )
        print(result.stdout, flush=True)
        self.assertEqual(result.returncode, 0, result.stdout)
