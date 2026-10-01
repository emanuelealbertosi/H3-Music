"""Choose the model store before setup, using the same transfer as the UI."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import model_store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', required=True)
    parser.add_argument('--existing', action='store_true')
    args = parser.parse_args()
    with model_store.exclusive(ROOT):
        model_store.check_idle(ROOT)
        result = model_store.relocate(ROOT, args.path, transfer=not args.existing)
    print('Cartella dei modelli: ' + result['path'])
    if result['warning']:
        print(result['warning'])


if __name__ == '__main__':
    main()
