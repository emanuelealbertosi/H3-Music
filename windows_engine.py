"""Enable the Windows engine's UTF-8 process code page, preserving its manifest."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import uuid
import xml.etree.ElementTree as ET

ASSEMBLY = 'urn:schemas-microsoft-com:asm.v1'
APPLICATION = 'urn:schemas-microsoft-com:asm.v3'
SETTINGS = 'http://schemas.microsoft.com/SMI/2019/WindowsSettings'


def with_utf8(original):
    tree = ET.fromstring(original)
    app = tree.find('{%s}application' % APPLICATION)
    if app is None:
        app = ET.SubElement(tree, '{%s}application' % APPLICATION)
    settings = app.find('{%s}windowsSettings' % APPLICATION)
    if settings is None:
        settings = ET.SubElement(app, '{%s}windowsSettings' % APPLICATION)
    page = settings.find('{%s}activeCodePage' % SETTINGS)
    if page is None:
        page = ET.SubElement(settings, '{%s}activeCodePage' % SETTINGS)
    page.text = 'UTF-8'
    ET.register_namespace('', ASSEMBLY)
    ET.register_namespace('asmv3', APPLICATION)
    ET.register_namespace('ws2019', SETTINGS)
    return ET.tostring(tree, encoding='utf-8', xml_declaration=True)


def resources(executable):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    ptr = ctypes.c_void_p
    kernel.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, ptr, wintypes.DWORD]
    kernel.LoadLibraryExW.restype = ptr
    kernel.FindResourceW.argtypes = [ptr, ptr, ptr]; kernel.FindResourceW.restype = ptr
    kernel.SizeofResource.argtypes = [ptr, ptr]; kernel.SizeofResource.restype = wintypes.DWORD
    kernel.LoadResource.argtypes = [ptr, ptr]; kernel.LoadResource.restype = ptr
    kernel.LockResource.argtypes = [ptr]; kernel.LockResource.restype = ptr
    kernel.FreeLibrary.argtypes = [ptr]
    handle = kernel.LoadLibraryExW(str(executable), None, 2)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        resource = kernel.FindResourceW(handle, 1, 24)
        if not resource:
            raise ValueError('Manifest del motore Windows non trovato.')
        size = kernel.SizeofResource(handle, resource)
        original = ctypes.string_at(kernel.LockResource(kernel.LoadResource(handle, resource)), size)
        languages = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, ptr, ptr, ptr, wintypes.WORD, wintypes.LPARAM)
        callback = callback_type(lambda _h, _t, _n, lang, _p: languages.append(lang) or 1)
        kernel.EnumResourceLanguagesW.argtypes = [ptr, ptr, ptr, callback_type, wintypes.LPARAM]
        if not kernel.EnumResourceLanguagesW(handle, 24, 1, callback, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        return original, languages
    finally:
        kernel.FreeLibrary(handle)


def enable_utf8(executable):
    executable = Path(executable)
    if os.name != 'nt':
        return False
    with executable.open('rb') as stream:
        if stream.read(2) != b'MZ':
            return False  # The execution check reports invalid executables.
    original, languages = resources(executable)
    root = ET.fromstring(original)
    if any(n.text == 'UTF-8' for n in root.iter('{%s}activeCodePage' % SETTINGS)):
        return False
    payload = with_utf8(original)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True); ptr = ctypes.c_void_p
    kernel.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]; kernel.BeginUpdateResourceW.restype = ptr
    kernel.UpdateResourceW.argtypes = [ptr, ptr, ptr, wintypes.WORD, ptr, wintypes.DWORD]
    kernel.EndUpdateResourceW.argtypes = [ptr, wintypes.BOOL]
    handle = kernel.BeginUpdateResourceW(str(executable), False)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_string_buffer(payload)
    try:
        for language in languages:
            if not kernel.UpdateResourceW(handle, 24, 1, language, buffer, len(payload)):
                raise ctypes.WinError(ctypes.get_last_error())
    except BaseException:
        kernel.EndUpdateResourceW(handle, True)
        raise
    if not kernel.EndUpdateResourceW(handle, False):
        raise ctypes.WinError(ctypes.get_last_error())
    return True


def prepare(root):
    """Caller holds the model lock and has verified an idle queue."""
    root = Path(root).resolve(); executable = root / 'runtime/engine/audiocpp_cli.exe'
    if os.name != 'nt' or not executable.is_file():
        return
    original, _ = resources(executable)
    if any(n.text == 'UTF-8' for n in ET.fromstring(original).iter('{%s}activeCodePage' % SETTINGS)):
        return
    import execution
    # Stage beside the current executable so CUDA/runtime DLLs are discoverable.
    staged = executable.with_name('unicode-ready-' + uuid.uuid4().hex + '.exe')
    backup = root / 'backups' / ('engine-before-unicode-' + uuid.uuid4().hex + '.exe')
    try:
        shutil.copy2(executable, staged)
        enable_utf8(staged)
        execution.check_engine(staged, 'cuda' if any(executable.parent.glob('cudart64*.dll')) else 'cpu')
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(executable, backup)
        staged.replace(executable)
    finally:
        staged.unlink(missing_ok=True)
