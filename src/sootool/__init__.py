from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _v

try:
    __version__ = _v("sootool")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"


def main() -> None:
    print("Hello from sootool!")
