"""Executable paths and host capabilities shared by Windows and macOS."""
import os
from pathlib import Path
import subprocess
import sys


def windows():return sys.platform=='win32'
def macos():return sys.platform=='darwin'
def binary(root,name,engine=False):
 return Path(root)/'runtime'/('engine' if engine else '')/(name+('.exe' if windows() else ''))
def python(root,component='python'):
 return Path(root)/'runtime'/component/('python.exe' if windows() else 'bin/python')
def backends():return ['cpu','metal'] if macos() else ['cpu','cuda'] if windows() else ['cpu']
def transcription_backend(backend):return 'cuda' if backend=='cuda' else 'cpu'
def setup_name():return 'Installa-Mac.command' if macos() else 'install.bat'
def open_folder(path):
 if windows():os.startfile(path)
 else:subprocess.Popen(['open' if macos() else 'xdg-open',str(path)])
