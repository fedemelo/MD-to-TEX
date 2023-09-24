import re
from typing import Tuple


def md_to_tex(file_path: str) -> None:
    """
    Converts a Markdown file into a LaTeX file.
    """
    md_file = open(file_path, "r")
    md_text = md_file.read()
    md_file.close()

    filename = file_path.split("\\")[-1][:-3]
    tex_path = r"C:\Users\feder\OneDrive - Universidad de los Andes\Académico\Apuntes\LaTeX\\"+filename+".tex"

    with open(tex_path, "w") as tex_file:
        tex_file.write(parse_mkdown(md_text, filename))
        tex_file.close()


def parse_mkdown(text: str, title: str) -> str:
    """
    Parses a string of (extended) Markdown text and returns the corresponding LaTeX code.
    """
    # Temporal complexity: O(n)

    position: int = 0
    tex_text: str = initial_tex_text(title)

    while position < len(text):

        add_to_tex, offset = parse_char(text[position:])

        tex_text += add_to_tex
        position += offset

    return tex_text


def TEXify_block(text: str) -> str:
    """
    Parses a block of text and returns the corresponding LaTeX code.
    """
    position: int = 0
    tex_text: str = ""

    while position < len(text):

        add_to_tex, offset = parse_char(text[position:])

        tex_text += add_to_tex
        position += offset

    return tex_text


def initial_tex_text(titulo: str) -> str:

    return r"""\documentclass{fmbnotes}
\usepackage{fmbmath}

\begin{document}

\newcommand*{\titulo}{"""+titulo+r"""}
\portada{\titulo} 

\begin{center}
{\Large\bfseries\sffamily \titulo}
\end{center}
"""


def parse_char(text: str) -> Tuple[str, int]:
    """
    Parses a block of text and returns the corresponding LaTeX code and the offset.
    """

    if not text:
        return "", 1

    char: str = text[0]
    add_to_tex: str = ""

    match char:

        case r"#":
            add_to_tex, offset = parse_title_or_tag(text)

        case r"*":
            add_to_tex, offset = parse_bold_or_italic(text)

        case r"-":
            add_to_tex, offset = parse_list(text)

        case r"$":
            add_to_tex, offset = parse_math(text)

        case r"!":
            add_to_tex, offset = parse_image(text)

        # case r"[":
            # add_to_tex, offset = parse_link(text)

        # case r"`":
            # add_to_tex, offset = parse_code(text)

        # case "0"|"1"|"2"|"3"|"4"|"5"|"6"|"7"|"8"|"9":
            # add_to_tex, offset = parse_possible_numbered_list(text)

        case _:    # Not MD syntax
            add_to_tex = char
            offset = 1

    return add_to_tex, offset


def parse_title_or_tag(text: str) -> str:

    next_char: str = text[1]
    add_to_tex, offset = parse_title(
        text) if next_char == r" " or next_char == r"#" else parse_tag(text)

    return add_to_tex, offset


def parse_tag(text: str) -> str:
    """
    E.g. #tag1 ...
    Tags are turned into comments 
    """
    offset = re.search(r'\s', text).start()

    body: str = text[1:offset]

    add_to_tex = r"%"+body+"\n"

    return add_to_tex, offset


def parse_title(text: str) -> str:
    """
    E.g. # Title 1, ## Title 2, ### Title 3, etc.
    """

    number_of_hashtags: int = 0
    offset: int = 0
    char = text[offset]
    while char == r"#":
        number_of_hashtags += 1
        offset += 1
        char = text[offset]

    # At this point, char must be a space
    offset += 1
    end_of_line = text.find("\n", offset)

    body: str = text[offset:end_of_line]

    body_as_tex = TEXify_block(body)

    add_to_tex = TEX_macro("level", [number_of_hashtags, body_as_tex])

    return add_to_tex, end_of_line


def parse_bold_or_italic(text: str) -> str:
    """
    E.g. *italic*, **bold**, ***bold and italic***
    """
    number_of_stars: int = 0
    offset: int = 0
    char: str = text[offset]
    while char == r"*":
        number_of_stars += 1
        offset += 1
        char = text[offset]

    match = re.search(r'(?<!\\)\*+', text[offset:])
    end_of_block = match.start()+offset
    end_offset = match.end()+offset
    body: str = text[offset:end_of_block]

    body_as_tex = TEXify_block(body)

    match number_of_stars % 4:
        case 1:
            add_to_tex = r"\textit{"+body_as_tex+r"}"
        case 2:
            add_to_tex = r"\textbf{"+body_as_tex+r"}"
        case 3:
            add_to_tex = r"\textit{\textbf{"+body_as_tex+r"}}"

    return add_to_tex, end_offset


def parse_list(text: str) -> str:
    """
    E.g. - Item 1\n- Item 2
    """
    if text[1] != r" ":
        return "-", 1

    items: list = []
    offset: int = 0
    while text[offset] == r"-":
        next_newline = text.find(r"\n")
        item = TEXify_block(text[offset:next_newline])
        items.append(TEX_macro(item)+item[1:])
        offset = next_newline+1

    itemize_body = ""
    for item in items:
        itemize_body += "    " + item + "\n"

    add_to_tex = TEX_environment("itemize", [], itemize_body[:-1])

    return add_to_tex, offset


def parse_math(text: str) -> str:
    """
    E.g. $x^2$ or $$A' = \Omega \setminus A\\A' = \{x \in \Omega | x \notin A\}$$
    """

    if text[1] != r"$":
        add_to_tex, offset = parse_inline_math(text)
    else:
        add_to_tex, offset = parse_display_math(text)

    return add_to_tex, offset


def parse_inline_math(text: str) -> str:
    """
    E.g. $x^2$
    """
    re_match = re.search(r'(?<!\\)\$', text[1:])
    end_of_block = re_match.end()
    body: str = text[1:end_of_block]

    add_to_tex = r"\("+body+r"\)"

    return add_to_tex, end_of_block+1


def parse_display_math(text: str) -> str:
    """
    E.g. $$A' = \Omega \setminus A\\A' = \{x \in \Omega | x \notin A\}$$
    """
    end_of_block = re.search(r'(?<!\\)\$\$', text[2:]).end()
    body: str = text[2:end_of_block]

    add_to_tex = TEX_environment("equation", [], body)

    return add_to_tex, end_of_block+2


def parse_image(text: str) -> str:
    """
    E.g. ![alt text](image.png)
    """
    if text[1] != r"[" or text[2] != r"[":
        return "!", 1

    end_of_alt_text = text.find(r"]]")
    filename = text[3:end_of_alt_text]

    add_to_tex = TEX_image(filename)

    return add_to_tex, end_of_alt_text+2


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

    environment += r"\end{"+name+"}"

    return environment


def TEX_image(filename: str, caption: str = "") -> str:
    s = "\n" + r"""\begin{figure}[h]
    \centering
    \includegraphics[0.6\textwidth]{./img/"""+filename+"}"+"\n"

    if caption != "":
        s += r"%TODO: \caption{\centering Falta caption }"+"\n"
    else:
        s += r"\caption{\centering "+caption+"}\n"

    extension_pos = filename.find(".")
    s += r"\label{fig:"+filename[:extension_pos]+"}\n"

    s += r"\end{figure}" + "\n"


def indent(text: str, number_of_spaces: int = 4) -> str:
    """
    Returns a string with the text indented.
    """

    text = text.replace("\n", "\n"+" "*number_of_spaces)
    return " "*number_of_spaces + text


def main():
    md_filename = input("Enter the name of the Markdown file: ")
    if not md_filename:
        md_filename = "test.md"
    elif not md_filename.endswith(".md"):
        md_filename += ".md"

    path: str = r"C:\Users\feder\OneDrive - Universidad de los Andes\Académico\Apuntes\Markdown\\"+md_filename
    md_to_tex(path)


main()