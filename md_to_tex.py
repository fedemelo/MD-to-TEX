import shutil
from typing import Tuple
from re import search, match, sub
from text_unidecode import unidecode
from TEX_lang import initial_tex_text, normalize_text, TEX_macro, TEX_environment, indent


def md_to_tex(md_path: str, tex_path: str) -> None:
    """
    Converts a Markdown file into a LaTeX file.
    """
    md_file = open(md_path, "r")
    md_text = md_file.read()
    md_file.close()

    md_filename = md_path.split("\\")[-1][:-3]

    backup_path = "backup.tex"
    try:
        shutil.copy2(tex_path, backup_path)
    except FileNotFoundError:
        pass

    with open(tex_path, "w") as tex_file:
        tex_file.write(parse_mkdown(md_text, md_filename))
        tex_file.close()


def parse_mkdown(text: str, title: str) -> str:
    """
    Parses a string of (extended) Markdown text and returns the corresponding LaTeX code.
    """
    # Temporal complexity: O(n)

    text = "\n" + text + "\n"

    tex_text: str = initial_tex_text(title)

    tex_text += TEXify_block(text) + "\n" + r"\end{document}"

    return tex_text


def TEXify_block(block: str) -> str:
    """
    Parses a block of Markdown text and returns the corresponding LaTeX code.
    """
    position: int = 1
    tex_text: str = ""
    block = " " + block + " "

    while position < len(block):

        add_to_tex, offset = parse_char(block[position-1:], 1)

        tex_text += add_to_tex
        position += offset

    return tex_text.strip()


def parse_char(text: str, offset: int) -> Tuple[str, int]:
    """
    Parses a block of text and returns the corresponding LaTeX code and the offset.

    If the character is not part of the Markdown syntax, it is returned as is.

    If the character is part of the Markdown syntax, the corresponding function is called.
    """

    char: str = text[offset]
    add_to_tex: str = ""

    match char:

        case r"%":
            add_to_tex, offset = r"\%", 1

        case r"$":
            add_to_tex, offset = check_if_math(text, offset)

        case r"*":
            add_to_tex, offset = parse_bold_or_italic(text, offset)

        case r"#":
            add_to_tex, offset = check_if_title_or_tag(text, offset)

        case r"-":
            add_to_tex, offset = check_if_list(text, offset)

        case r"!":
            add_to_tex, offset = check_if_image(text, offset)

        case r"[":
            add_to_tex, offset = check_if_link(text, offset)

        case r">":
            add_to_tex, offset = check_if_highlight(text, offset)

        case r"`":
            add_to_tex, offset = check_if_code(text, offset)

        # case "0"|"1"|"2"|"3"|"4"|"5"|"6"|"7"|"8"|"9":
            # add_to_tex, offset = parse_possible_numbered_list(text, offset)

        case _:    # Not MD syntax
            add_to_tex = char
            offset = 1

    return add_to_tex, offset

# ========================== Math ==========================


def check_if_math(text: str, offset: int) -> str:

    # It is math if the character immediately after $ is not whitespace:
    try:
        if not text[offset+1].isspace():
            if text[offset+1] == "$":
                add_to_tex, offset = parse_display_math(text[offset:])
            else:
                add_to_tex, offset = parse_inline_math(text[offset:])
        else:
            add_to_tex = "$"
            offset = 1
    except IndexError:
        add_to_tex = "$"
        offset = 1

    return add_to_tex, offset


def parse_inline_math(text: str) -> str:
    """
    E.g. "$x^2$"
    """
    re_match = search(r'(?<!\\)\$', text[1:])
    end_of_block = re_match.end()
    body: str = text[1:end_of_block]

    add_to_tex = r"\("+body+r"\)"

    return add_to_tex, end_of_block+1


def parse_display_math(text: str) -> str:
    """
    E.g. "$$A' = \Omega \setminus A\\A' = \{x \in \Omega | x \notin A\}$$"
    """
    end_of_block = search(r'(?<!\\)\$\$', text[2:]).end()
    body: str = text[2:end_of_block]

    add_to_tex = TEX_environment("equation*", [], body)

    if r"\begin{gather}" in add_to_tex:
        add_to_tex = add_to_tex.replace(r"\begin{gather}", r"\begin{gather*}")
        add_to_tex = add_to_tex.replace(r"\end{gather}", r"\end{gather*}")
        add_to_tex = add_to_tex.replace(r"\begin{equation*}", "")
        add_to_tex = add_to_tex.replace(r"\end{equation*}", "")

    return add_to_tex, end_of_block+2

# ========================== Math ==========================
# ========================== Bold or italic ==========================


def parse_bold_or_italic(text: str, offset: int) -> str:
    """
    E.g. "*italic*", "**bold**", "***bold and italic***"
    """
    number_of_stars: int = 0
    char: str = text[offset]
    while char == r"*":
        number_of_stars += 1
        offset += 1
        char = text[offset]

    match = search(r'(?<!\\)\*+', text[offset:])
    end_of_block = match.start()+offset
    end_offset = match.end()+offset
    body: str = text[offset:end_of_block]

    body_as_tex = TEXify_block(body)

    match number_of_stars % 4:
        case 1:
            add_to_tex = r"\textit{"+body_as_tex+r"}"
        case 2:
            add_to_tex = r"\textbf{"+body_as_tex+r"}"
        case 3 | 0:
            add_to_tex = r"\textit{\textbf{"+body_as_tex+r"}}"

    return add_to_tex, end_offset-1

# ========================== Bold or italic ==========================
# ========================== Title or tag ==========================


def check_if_title_or_tag(text: str, offset: int) -> str:

    # It is a title if the character before is \n and after is a space
    if text[offset-1] == "\n" and text[offset+1] in (" ", "#"):
        add_to_tex, local_offset = parse_title(text[offset:])

    # It is a tag if the character before is some whitespace and after is a letter
    elif text[offset-1].isspace() and text[offset+1].isalpha():
        add_to_tex, local_offset = parse_tag(text[offset:])

    else:
        add_to_tex = "#"
        local_offset = 1

    return add_to_tex, offset+local_offset


def parse_title(text: str) -> str:
    """
    E.g. "# Title 1", "## Title 2", "### Title 3"
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

    title: str = text[offset:end_of_line]

    title_as_tex = TEXify_block(title)

    add_to_tex = TEX_macro("level", [number_of_hashtags, title_as_tex])+"\n"
    add_to_tex += r"\label{sec:"+normalize_text(title_as_tex)+"}"+"\n"

    return add_to_tex, end_of_line


def parse_tag(text: str) -> str:
    """
    E.g. "#tag1 "
    Tags are turned into comments 
    """
    offset = search(r'\s', text).start()

    body: str = text[1:offset]

    add_to_tex = r"%"+body+"\n"

    return add_to_tex, offset

# ========================== Title or tag ==========================
# ========================== List ==========================


def check_if_list(text: str, offset: int) -> str:

    # It is a list if the character before "-" is \n and after is a space
    try:
        if text[offset-1] == "\n" and text[offset+1] in (" "):
            # The text is given as "\n- Item..."
            add_to_tex, local_offset = parse_list(text[offset-1:])
            return add_to_tex, offset+local_offset
        else:
            return "-", 1
    except IndexError:
        return "-", 1


def parse_list(text: str) -> str:
    """
    E.g. "\n- Item 1\n- Item 2"
    """

    items = []
    offset = 1
    while (text[offset-1] == "\n" and
           text[offset] == r"-" and
           text[offset+1] == " "):
        next_newline = text.find("\n", offset+1)
        item_text = text[offset+2:next_newline]
        item = TEXify_block(item_text)
        items.append(f"\\item {item}\n")
        offset = next_newline+1

    itemize_body = "".join(items)

    add_to_tex = TEX_environment("itemize", [], itemize_body[:-1])

    return add_to_tex, offset-2


# ========================== List ==========================
# ========================== Image ==========================


def check_if_image(text: str, offset: int) -> str:

    if offset+2 >= len(text):
        return "!", 1

    # It is an image if the character before "!" is "\n" and after is "[["
    elif text[offset-1] == "\n" and text[offset+1:offset+3] == r"[[":
        add_to_tex, local_offset = parse_image(text[offset:])

    else:
        add_to_tex = "!"
        local_offset = 1

    return add_to_tex, offset+local_offset


def parse_image(text: str) -> str:
    """
    E.g. ![[alt text]]
    """
    end_of_alt_text = text.find(r"]]")
    filename = text[3:end_of_alt_text]
    if filename.__contains__("|"):
        filename = filename[:filename.find(r"|")]

    add_to_tex = TEX_image(filename)

    return add_to_tex, end_of_alt_text+2


def TEX_image(filename: str, caption: str = "") -> str:
    s = "\n" + r"""\begin{figure}[h]
    \centering
    \includegraphics[width=0.6\textwidth]{./img/"""+filename+"}"+"\n"

    if caption:
        s += " "*4 + r"\caption{\centering "+caption+"}"+"\n"
    else:
        s += " "*4 + \
            r"\caption{\centering \textcolor{red}{TODO: " + \
            filename.replace("_", " ")+r"}}"+"\n"

    extension_pos = filename.find(".")
    s += " "*4 + r"\label{fig:"+filename[:extension_pos]+"}\n"

    s += r"\end{figure}" + "\n"

    return s


# ========================== Image ==========================
# ========================== Link ==========================


def check_if_link(text: str, offset: int) -> str:

    # It is a link if the character after is also "["
    if text[offset+1] == "[":
        add_to_tex, local_offset = parse_link(text[offset:])

    else:
        add_to_tex = "["
        local_offset = 1

    return add_to_tex, offset+local_offset


def parse_link(text: str) -> str:
    """
    E.g. "[[document#section|link]]"
    """
    end_of_link_ref = text.find(r"|")
    start_of_link_ref = text.find(r"#")
    link_ref = text[start_of_link_ref+1:end_of_link_ref]

    end_of_link = text.find(r"]]")
    link_text = text[end_of_link_ref+1:end_of_link]

    link_ref_as_tex = TEXify_block(link_ref)
    ref_to_label = "sec:"+normalize_text(link_ref_as_tex)

    add_to_tex = r"\hyperref["+ref_to_label+"]{"+link_text+"}"

    return add_to_tex, end_of_link+1


# ========================== Link ==========================
# ========================== Highlight ==========================


def check_if_highlight(text: str, offset: int) -> str:

    # It is a highlight if the character before ">" is "\n"
    if text[offset-1] == "\n":
        add_to_tex, local_offset = parse_highlight(text[offset:])

    else:
        add_to_tex = ">"
        local_offset = 1

    return add_to_tex, offset+local_offset


def parse_highlight(text: str) -> str:
    """
    E.g. 
> [!tip] Teorema de Erdös-Gallai
>Sea tal cosa $A$ y tal otra $B$."
    """
    open_square_bracket = text.find("[")
    if open_square_bracket == -1 or text[open_square_bracket+1] != "!":
        name_of_highlight = ""

    close_square_bracket = text.find("]")
    # type_of_highlight = text[open_square_bracket+2:close_square_bracket]
    end_of_line_pos = text.find("\n")
    name_of_highlight = text[close_square_bracket+1:end_of_line_pos].strip()

    highlight_start = end_of_line_pos+1
    end_of_line = text[end_of_line_pos]
    char = text[highlight_start]

    while end_of_line == "\n" and char == ">":
        end_of_line_pos = text.find("\n", end_of_line_pos+1)
        end_of_line = text[end_of_line_pos]
        char = text[end_of_line_pos+1]
    # This cicle ends as soon as a line starts with something other than ">"

    end_of_highlight = end_of_line_pos+1
    content = text[highlight_start+1:end_of_highlight]
    content = content.replace(r">", "")
    highlight_content = TEXify_block(content)

    normalized_name = normalize_text(name_of_highlight)

    if "definicion.lower()" in normalized_name:
        add_to_tex = TEX_environment("definicion", [
            name_of_highlight.strip(), f"def:{normalized_name}"], highlight_content)
    elif "notacion.lower()" in normalized_name:
        add_to_tex = TEX_environment("notacion", [
            name_of_highlight.strip(), f"not:{normalized_name}"], highlight_content)
    elif "ejemplo.lower()" in normalized_name:
        add_to_tex = TEX_environment("ejemplo", [
            name_of_highlight.strip(), f"ej:{normalized_name}"], highlight_content)
    else:
        add_to_tex = TEX_environment("teorema", [
            name_of_highlight.strip(), f"thm:{normalized_name}"], highlight_content)
        
    return add_to_tex, end_of_highlight


# ========================== Highlight ==========================
# ========================== Code ==========================

def check_if_code(text: str, offset: int) -> str:

    # It is a code block if the characters are "```"
    if text[offset+1] == "`" and text[offset+2] == "`":
        add_to_tex, local_offset = parse_code_block(text[offset+3:])

    else:
        add_to_tex, local_offset = parse_code(text[offset+1:])

    return add_to_tex, offset+local_offset


def parse_code_block(text: str) -> str:
    """
    E.g.
```
    code
```
    """
    end_of_block = text.find("```")

    if text[0] != "\n":
        end_of_line = text.find("\n")
        language = text[:end_of_line]
        code = text[end_of_line+1:end_of_block-1]
    else:
        language = ""
        code = text[1:end_of_block-1]

    language = "JavaScript" if normalize_text(language) in ["js", "jsx", "tsx", "ts"] else language
    optional_params = [f"language={language}"] if language else []

    add_to_tex = TEX_environment("lstlisting", [], code, optional_params, indentation=False)

    return add_to_tex, end_of_block+3


def parse_code(text: str) -> str:
    """
    E.g. `code`
    """
    end_of_block = text.find("`")
    code = text[:end_of_block]

    add_to_tex = r"\verb|"+code+r"|"

    return add_to_tex, end_of_block+1


# ========================== Code ==========================
# ========================== Numbered list ==========================


# ========================== Numbered list ==========================
# ========================== Table ==========================


# ========================== Table ==========================
# Main

def main(md_path: str, tex_path: str) -> None:
    md_to_tex(md_path, tex_path)


MD_PATH = r"C:\Users\feder\OneDrive - Universidad de los Andes\Académico\Apuntes\Markdown\Grafos\Teoría de Grafos.md"
TEX_PATH = r"C:\Users\feder\OneDrive - Universidad de los Andes\Académico\Apuntes\LaTeX\matematica\grafos\grafos.tex"

main(MD_PATH, TEX_PATH)
