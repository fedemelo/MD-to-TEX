from text_unidecode import unidecode
from re import sub


def initial_tex_text(titulo: str) -> str:

    return r"""% !TeX spellcheck = es_ES
\documentclass{fmbnotes}
\usepackage{fmbmath}

\begin{document}

\newcommand*{\titulo}{"""+titulo+r"""}
\portada{\titulo} 

\begin{center}
    {\Large\bfseries\sffamily \titulo}
\end{center}

"""


def normalize_text(s: str) -> str:
    """
    Returns the text normalized.
    """
    sin_acentos = unidecode(s.strip())
    underscore_por_espacios_y_puntuacion = sub(r'\W+', '_', sin_acentos)
    return underscore_por_espacios_y_puntuacion.lower()


def TEX_macro(name: str, params: list = [], optional_params: list = []) -> str:
    """
    Returns a string with the macro name and its parameters.
    """
    macro: str = fr"\{name}"

    for param in optional_params:
        macro += "[" + str(param) + "]"

    for param in params:
        macro += "{" + str(param) + "}"

    return macro


def TEX_environment(name: str, params: list, body: str, optional_params: list = [], ) -> str:
    """
    Returns a string with the environment name and its parameters.
    """
    environment: str = "\n"+r"\begin{"+name+"}"

    for param in optional_params:
        environment += "[" + str(param) + "]"

    for param in params:
        environment += "{" + str(param) + "}"

    environment += "\n"
    environment += indent(body)
    environment += "\n"

    environment += r"\end{"+name+"}" + "\n"

    return environment


def indent(text: str, number_of_spaces: int = 4) -> str:
    """
    Returns a string with the text indented.
    """

    text = text.replace("\n", "\n"+" "*number_of_spaces)
    return " "*number_of_spaces + text
