"""Installer disk check for the selected models and their configured volume."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import macos_space
import model_store


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--quant', choices=('q4', 'q8', 'bf16', 'both', 'all'), default='both')
    args = parser.parse_args()
    with model_store.exclusive(ROOT):
        macos_space.check(ROOT, args.quant)
