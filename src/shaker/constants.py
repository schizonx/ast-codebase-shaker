"""Shared constants for Codebase Shaker.

All magic values, defaults, and lookup tables are defined here.
This module depends only on shaker.models to prevent circular imports.

Every other module in the codebase depends on this module.
"""

from __future__ import annotations

import builtins
import sys

from shaker.models import CompressionMode

DEFAULT_MODE: CompressionMode = CompressionMode.SIGNATURES

SUPPORTED_MODES: tuple[CompressionMode, ...] = (
    CompressionMode.FULL,
    CompressionMode.SIGNATURES,
    CompressionMode.STRIP,
)

DEFAULT_ENCODING: str = "utf-8"

FALLBACK_ENCODING: str = "latin-1"

OMIT_THRESHOLD: int = 50

TIKTOKEN_DEFAULT_ENCODING: str = "cl100k_base"

CHARS_PER_TOKEN_FALLBACK: int = 4

BUILTIN_NAMES: frozenset[str] = frozenset(dir(builtins))

_STDLIB_MODULE_NAMES: tuple[str, ...] = (
    "__future__",
    "_thread",
    "abc",
    "aifc",
    "argparse",
    "array",
    "ast",
    "asynchat",
    "asyncio",
    "asyncore",
    "atexit",
    "audioop",
    "base64",
    "bdb",
    "binascii",
    "binhex",
    "bisect",
    "builtins",
    "bz2",
    "calendar",
    "cgi",
    "cgitb",
    "chunk",
    "cmath",
    "cmd",
    "code",
    "codecs",
    "codeop",
    "collections",
    "colorsys",
    "compileall",
    "concurrent",
    "configparser",
    "contextlib",
    "contextvars",
    "copy",
    "copyreg",
    "cProfile",
    "crypt",
    "csv",
    "ctypes",
    "curses",
    "dataclasses",
    "datetime",
    "dbm",
    "decimal",
    "difflib",
    "dis",
    "distutils",
    "doctest",
    "email",
    "encodings",
    "enum",
    "errno",
    "faulthandler",
    "fcntl",
    "filecmp",
    "fileinput",
    "fnmatch",
    "formatter",
    "fractions",
    "ftplib",
    "functools",
    "gc",
    "getopt",
    "getpass",
    "gettext",
    "glob",
    "grp",
    "gzip",
    "hashlib",
    "heapq",
    "hmac",
    "html",
    "http",
    "idlelib",
    "imaplib",
    "imghdr",
    "imp",
    "importlib",
    "inspect",
    "io",
    "ipaddress",
    "itertools",
    "json",
    "keyword",
    "lib2to3",
    "linecache",
    "locale",
    "logging",
    "lzma",
    "mailbox",
    "mailcap",
    "marshal",
    "math",
    "mimetypes",
    "mmap",
    "modulefinder",
    "multiprocessing",
    "netrc",
    "nis",
    "nntplib",
    "numbers",
    "operator",
    "optparse",
    "os",
    "ossaudiodev",
    "pathlib",
    "pdb",
    "pickle",
    "pickletools",
    "pipes",
    "pkgutil",
    "platform",
    "plistlib",
    "poplib",
    "posix",
    "posixpath",
    "pprint",
    "profile",
    "pstats",
    "pty",
    "pwd",
    "py_compile",
    "pyclbr",
    "pydoc",
    "queue",
    "quopri",
    "random",
    "re",
    "readline",
    "reprlib",
    "resource",
    "rlcompleter",
    "runpy",
    "sched",
    "secrets",
    "select",
    "selectors",
    "shelve",
    "shlex",
    "shutil",
    "signal",
    "site",
    "smtpd",
    "smtplib",
    "sndhdr",
    "socket",
    "socketserver",
    "spwd",
    "sqlite3",
    "ssl",
    "stat",
    "statistics",
    "string",
    "stringprep",
    "struct",
    "subprocess",
    "sunau",
    "symtable",
    "sys",
    "sysconfig",
    "syslog",
    "tabnanny",
    "tarfile",
    "telnetlib",
    "tempfile",
    "termios",
    "test",
    "textwrap",
    "threading",
    "time",
    "timeit",
    "tkinter",
    "token",
    "tokenize",
    "trace",
    "traceback",
    "tracemalloc",
    "tty",
    "turtle",
    "turtledemo",
    "types",
    "typing",
    "unicodedata",
    "unittest",
    "urllib",
    "uu",
    "uuid",
    "venv",
    "warnings",
    "wave",
    "weakref",
    "webbrowser",
    "winreg",
    "winsound",
    "wsgiref",
    "xdrlib",
    "xml",
    "xmlrpc",
    "zipapp",
    "zipfile",
    "zipimport",
    "zlib",
    "zoneinfo",
)

_runtime_stdlib: frozenset[str] = (
    frozenset(sys.stdlib_module_names)
    if hasattr(sys, "stdlib_module_names")
    else frozenset()
)

STDLIB_MODULES: frozenset[str] = (
    frozenset(_STDLIB_MODULE_NAMES) | _runtime_stdlib
)

SECRET_PATTERNS: dict[str, str] = {
    "aws_access_key": r"(?:AKIA|ASIA)[A-Z0-9]{16}",
    "aws_secret_key": r"(?i)aws_secret_access_key\s*=\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?",
    "github_token": r"(?:ghp_|gho_|github_pat_)[A-Za-z0-9_]{36,}",
    "private_key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "generic_api_key": (
        r"(?i)(?:api_key|api_secret|password|token)"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}['\"]?"
    ),
    "env_secret": (
        r"(?i)(?:SECRET|PASSWORD|TOKEN|KEY)"
        r"\s*=\s*['\"]?[A-Za-z0-9_\-]{16,}['\"]?"
    ),
}
