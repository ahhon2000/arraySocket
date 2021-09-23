import sys, os
from pathlib import Path
from itertools import chain

def inclPath(*dirs, defaults=('core')):
    """Add each directory in dirs to sys.path, unless it is already there

    Also, the parent dir of this file and defaults will be added, if absent.
    
    To use this function in an script put the following lines at the beginning:


    import sys, pathlib; d = pathlib.Path(__file__).resolve()
    while d.parent != d and not (d / 'Common.py').exists(): d = d.parent
    sys.path.count(str(d)) or sys.path.insert(0,str(d)); from Common import inclPath

    Then you can include paths relative to the main directory like this:

    inclPath('maintenance', 'maintenance/tests')

    """

    dirs = list(dirs)
    dirs.extend(defaults)

    p0 = Path(__file__).resolve().parent
    for p in chain((p0,), map(lambda d: p0 / d, dirs)):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)

def importClassesFromPackage(packageInitFile):
    """Import classes from `class files'

    A `class file' is a *.py file such that its name starts with a capital
    letter and it contains a class of the same name.

    NOTE: This function does not itself import anything, it returns a script
    instead that should passed on to exec in the package's namespace.

    USAGE: In the package's __init__.py:
        exec(importClassesFromPackage(__file__))

    """

    ls = []
    for f in Path(packageInitFile).resolve().parent.iterdir():
        if f.suffix != '.py': continue
        if not f.is_file()  or  not f.stem[0].isupper(): continue
        modname = f.stem

        ls.append(f"from . import {modname} as tmpmod")
        ls.append(f"""
if hasattr(tmpmod, '{modname}'):
    from .{modname} import {modname}
"""[1:-1])

    scr = "\n".join(ls)

    return scr
