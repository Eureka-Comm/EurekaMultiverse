import pathlib
# Extend this package's __path__ to include the top-level 'src' directory
# This allows imports like 'src.eureka.universe' to resolve when tests are run from the 'eureka' subdirectory.
_top_src = pathlib.Path(__file__).resolve().parents[2] / "src"
if _top_src.is_dir():
    __path__.append(str(_top_src))
