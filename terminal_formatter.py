# Path: terminal_formatter.py
# (Reviewing existing code)

import re
import shutil
import textwrap
import os
import sys
from typing import Optional


class TerminalFormatter:
    """Gestisce la formattazione ANSI per output nel terminale."""

    # Codici ANSI (Keep all existing codes: RESET, BOLD, ITALIC, colors, etc.)
    RESET = "\033[0m"; BOLD = "\033[1m"; ITALIC = "\033[3m"; UNDERLINE = "\033[4m"
    DIM = "\033[2m"; REVERSE = "\033[7m"
    # Text Colors
    BLACK = "\033[30m"; RED = "\033[31m"; GREEN = "\033[32m"; YELLOW = "\033[33m"
    BLUE = "\033[34m"; MAGENTA = "\033[35m"; CYAN = "\033[36m"; WHITE = "\033[37m"
    # Bright Text Colors
    BRIGHT_BLACK = "\033[90m"; BRIGHT_RED = "\033[91m"; BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"; BRIGHT_BLUE = "\033[94m"; BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"; BRIGHT_WHITE = "\033[97m"
    # Background Colors
    BG_BLACK = "\033[40m"; BG_RED = "\033[41m"; BG_GREEN = "\033[42m"; BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"; BG_MAGENTA = "\033[45m"; BG_CYAN = "\033[46m"; BG_WHITE = "\033[47m"
    # Bright Background Colors
    BG_BRIGHT_BLACK = "\033[100m"; BG_BRIGHT_RED = "\033[101m"; BG_BRIGHT_GREEN = "\033[102m"
    BG_BRIGHT_YELLOW = "\033[103m"; BG_BRIGHT_BLUE = "\033[104m"; BG_BRIGHT_MAGENTA = "\033[105m"
    BG_BRIGHT_CYAN = "\033[106m"; BG_BRIGHT_WHITE = "\033[107m"


    # Definizioni delle espressioni regolari per Markdown-like syntax
    # Using more robust regex, especially for italics to avoid conflicts
    RE_BOLD_STARS = r'\*\*(.+?)\*\*' # Match non-greedy between **
    RE_BOLD_UNDERSCORES = r'__(.+?)__' # Match non-greedy between __
    # Italic regex needs to be careful not to match bold markers
    # Match * not preceded/followed by * or word char, and not followed by space
    # Match * not preceded by space, and not preceded/followed by * or word char
    RE_ITALIC_STARS = r'(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])'
    # Match _ not preceded/followed by _ or word char - simpler as _ is often part of words
    RE_ITALIC_UNDERSCORES = r'(?<![\w_])_(?!_)(.+?)(?<!_)_(?![\w_])'
    RE_UNDERLINE = r'~(.*?)~' # Simple underline marker
    RE_HIGHLIGHT = r'`(.*?)`' # Inline code / highlight
    RE_HEADING = r'^(#{1,6})\s+(.*?)$' # Match 1 to 6 # for headings
    RE_BULLET_LIST = r'^\s*([-*+])\s+(.*?)$' # Match -, *, + for bullets
    RE_NUMBER_LIST = r'^\s*(\d+)\.\s+(.*?)$' # Match 1. 2. etc.
    RE_QUOTE = r'^\s*>\s+(.*?)$' # Match > for blockquotes

    # Internal state for ANSI support detection
    _ansi_enabled = None

    @classmethod
    def supports_ansi(cls) -> bool:
        """Verifica se il terminale/ambiente corrente sembra supportare ANSI."""
        if cls._ansi_enabled is not None:
            return cls._ansi_enabled

        # Check for specific environment variables often present in modern terminals
        if os.environ.get('TERM') == 'dumb': # Dumb terminals definitely don't support it
            cls._ansi_enabled = False
            return False
        if os.environ.get('NO_COLOR') is not None: # Standard way to disable color
            cls._ansi_enabled = False
            return False
        if os.environ.get('COLORTERM') in ('truecolor', '24bit'):
            cls._ansi_enabled = True
            return True

        # Windows check (modern Windows Terminal, ConEmu, ANSICON)
        if os.name == 'nt':
            cls._ansi_enabled = (os.environ.get('WT_SESSION') is not None or
                                 os.environ.get('ConEmuANSI') == 'ON' or
                                 os.environ.get('ANSICON') is not None)
        else:
            # Unix-like check (stdout is a TTY)
            # Also check TERM environment variable for common values
            term = os.environ.get('TERM', '')
            cls._ansi_enabled = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and \
                                'xterm' in term or 'screen' in term or 'vt100' in term or 'linux' in term
        return cls._ansi_enabled

    @classmethod
    def enable_ansi(cls, enabled: bool = True):
        """Forza l'abilitazione o disabilitazione dell'output ANSI."""
        cls._ansi_enabled = enabled

    @staticmethod
    def get_terminal_width(default: int = 80, max_width: int = 120) -> int:
        """Ottiene la larghezza del terminale, con un fallback e un massimo."""
        try:
            columns, _ = shutil.get_terminal_size(fallback=(default, 24))
            # Apply a maximum width to prevent issues with extremely wide terminals
            return min(columns, max_width) if columns > 0 else default
        except (AttributeError, OSError, ValueError):
            # ValueError can happen in some environments like certain IDE run windows
            return default

    @classmethod
    def format_heading(cls, text: str, level: int) -> str:
        """Formatta un'intestazione con stile appropriato."""
        if level == 1:
            # H1: Bold, Bright White on Blue background
            return f"{cls.BG_BLUE}{cls.BRIGHT_WHITE}{cls.BOLD} {text} {cls.RESET}"
        elif level == 2:
            # H2: Bold, Underlined, Bright Magenta
            return f"{cls.BRIGHT_MAGENTA}{cls.BOLD}{cls.UNDERLINE}{text}{cls.RESET}"
        elif level == 3:
            # H3: Bold, Bright Cyan
            return f"{cls.BRIGHT_CYAN}{cls.BOLD}{text}{cls.RESET}"
        else: # H4+
            # H4+: Bold, Yellow
            return f"{cls.YELLOW}{cls.BOLD}{text}{cls.RESET}"

    @classmethod
    def format_terminal_text(cls, text: str, width: Optional[int] = None) -> str:
        """
        Formatta il testo per il terminale, applicando stili markdown-like se ANSI è supportato.
        """
        effective_width = width if width is not None else cls.get_terminal_width()

        # If ANSI not supported, use plain formatter
        if not cls.supports_ansi():
            return cls.plain_text_formatter(text, width=effective_width)

        formatted_lines = []
        in_code_block = False # Basic state for potential future code block handling

        # Split lines but preserve trailing newline if present
        lines = text.splitlines() # Handles different newline types

        for line in lines:
            original_line = line # For fallback/debugging

            # --- Block Element Formatting (Applied first) ---
            processed_block = False

            # Headings
            heading_match = re.match(cls.RE_HEADING, line)
            if heading_match:
                level = len(heading_match.group(1))
                content = heading_match.group(2).strip()
                formatted_lines.append(cls.format_heading(content, level))
                processed_block = True

            # Blockquotes (apply dim/italic style)
            elif re.match(cls.RE_QUOTE, line):
                m = re.match(cls.RE_QUOTE, line)
                # Recursively format the quote content for inline styles
                quote_content = cls.format_inline_styles(m.group(1))
                # Apply wrapping to the quote content *after* inline formatting
                wrapped_quote = textwrap.wrap(quote_content, width=effective_width - 2) # Indent by 2
                formatted_lines.extend([f"{cls.DIM}{cls.ITALIC}{cls.CYAN}> {wq}{cls.RESET}" for wq in wrapped_quote])
                processed_block = True

            # Bullet Lists (apply color and bullet)
            elif re.match(cls.RE_BULLET_LIST, line):
                m = re.match(cls.RE_BULLET_LIST, line)
                bullet = m.group(1) # Could use specific bullet chars based on group(1) if desired
                # Recursively format list item content
                item_content = cls.format_inline_styles(m.group(2))
                wrapped_item = textwrap.wrap(item_content, width=effective_width - 4) # Indent bullet list
                formatted_lines.append(f"{cls.YELLOW}  {bullet} {cls.RESET}{wrapped_item[0]}")
                formatted_lines.extend([f"    {line}" for line in wrapped_item[1:]])
                processed_block = True

            # Numbered Lists
            elif re.match(cls.RE_NUMBER_LIST, line):
                m = re.match(cls.RE_NUMBER_LIST, line)
                number = m.group(1)
                item_content = cls.format_inline_styles(m.group(2))
                wrapped_item = textwrap.wrap(item_content, width=effective_width - (len(number) + 3)) # Adjust indent
                formatted_lines.append(f"{cls.YELLOW} {number}. {cls.RESET}{wrapped_item[0]}")
                formatted_lines.extend([f"  {' ' * len(number)}. {line}" for line in wrapped_item[1:]]) # Align subsequent lines
                processed_block = True


            # --- Inline Formatting and Wrapping (if not a processed block element) ---
            if not processed_block:
                # Apply inline styles first
                formatted_line = cls.format_inline_styles(line)

                # Wrap the line after inline styles are applied
                try:
                    # Handle empty lines correctly
                    wrapped_lines = textwrap.wrap(formatted_line, width=effective_width) if formatted_line.strip() else ['']
                    formatted_lines.extend(wrapped_lines)
                except Exception as e:
                    # Fallback if wrapping fails (e.g., complex ANSI sequences)
                    print(f"{cls.RED}Warning: Text wrapping failed for line: {original_line} (Error: {e}){cls.RESET}", file=sys.stderr)
                    formatted_lines.append(original_line) # Append original line on error

        return '\n'.join(formatted_lines)

    @classmethod
    def format_inline_styles(cls, line: str) -> str:
        """Applies inline formatting (bold, italic, etc.) using regex."""
        # Apply styles in a specific order to avoid conflicts (e.g., bold first)
        line = re.sub(cls.RE_BOLD_STARS, f"{cls.BOLD}\\1{cls.RESET}", line)
        line = re.sub(cls.RE_BOLD_UNDERSCORES, f"{cls.BOLD}\\1{cls.RESET}", line)
        line = re.sub(cls.RE_ITALIC_STARS, f"{cls.ITALIC}\\1{cls.RESET}", line)
        line = re.sub(cls.RE_ITALIC_UNDERSCORES, f"{cls.ITALIC}\\1{cls.RESET}", line)
        line = re.sub(cls.RE_UNDERLINE, f"{cls.UNDERLINE}\\1{cls.RESET}", line)
        line = re.sub(cls.RE_HIGHLIGHT, f"{cls.REVERSE}\\1{cls.RESET}", line) # Often used for `code`
        return line

    @staticmethod
    def plain_text_formatter(text: str, width: Optional[int] = None) -> str:
        """
        A simple formatter that removes markdown and wraps text.
        """
        effective_width = width if width is not None else TerminalFormatter.get_terminal_width()

        cleaned_lines = []
        lines = text.splitlines()

        for line in lines:
            # Remove markdown formatting for plain text output
            line = re.sub(r'\*\*(.+?)\*\*', r'\1', line) # Bold
            line = re.sub(r'__(.+?)__', r'\1', line)     # Bold
            line = re.sub(r'(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])', r'\1', line) # Italic *
            line = re.sub(r'(?<![\w_])_(?!_)(.+?)(?<!_)_(?![\w_])', r'\1', line) # Italic _
            line = re.sub(r'~(.*?)~', r'\1', line)       # Underline
            line = re.sub(r'`(.*?)`', r'\1', line)       # Highlight/Code

            # Handle block elements simply
            line = re.sub(r'^(#{1,6})\s+', '', line)      # Remove heading markers
            line = re.sub(r'^\s*([-*+])\s+', '  * ', line) # Convert bullets to '* '
            line = re.sub(r'^\s*(\d+)\.\s+', r'  \1. ', line) # Keep numbers but indent
            line = re.sub(r'^\s*>\s+', '> ', line)        # Keep quote marker

            # Wrap the cleaned line
            if line.strip():
                cleaned_lines.extend(textwrap.wrap(line, width=effective_width))
            else:
                cleaned_lines.append('') # Preserve empty lines

        return '\n'.join(cleaned_lines)

    @classmethod
    def color_text(cls, text: str, color_code: str) -> str:
        """Applies a specific ANSI color code if supported, otherwise returns original text."""
        if cls.supports_ansi():
            return f"{color_code}{text}{cls.RESET}"
        return text

# ===========================================
#  Blocco di Test Eseguibile (__main__)
# ===========================================
# (Keep the existing if __name__ == '__main__' block for visual testing)
if __name__ == '__main__':
    # Test ANSI support detection
    print(f"{TerminalFormatter.BOLD}--- Terminal ANSI Support Test ---{TerminalFormatter.RESET}")
    if TerminalFormatter.supports_ansi():
        print(f"{TerminalFormatter.GREEN}✓ ANSI support detected/enabled.{TerminalFormatter.RESET}")
    else:
        # Try enabling ANSI explicitly on Windows if possible (requires OS-level support)
        if os.name == 'nt':
            os.system('') # This can sometimes enable ANSI processing in cmd.exe/powershell
            if TerminalFormatter.supports_ansi(): # Check again
                print(f"{TerminalFormatter.YELLOW}✓ ANSI support enabled (likely via OS trick).{TerminalFormatter.RESET}")
            else:
                print(f"{TerminalFormatter.RED}⚠ ANSI support not detected. Formatting will be plain text.{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.RED}⚠ ANSI support not detected. Formatting will be plain text.{TerminalFormatter.RESET}")

    # --- Visual Formatting Test ---
    print(f"\n{TerminalFormatter.BOLD}--- Visual Formatting Test ---{TerminalFormatter.RESET}")
    sample_text = """# Intestazione Livello 1
Questo è testo normale sotto H1. Contiene **grassetto**, *corsivo*, ~sottolineato~ e `codice inline`. _Anche underscore italici_. __E bold__.

## Intestazione Livello 2 con `codice`
Paragrafo dopo H2.
> Questo è un blocco citazione.
> Può contenere **formattazione** *inline*.
> Si estende su più righe.

### Lista Puntata (H3)
- Primo elemento
- Secondo con *corsivo*
  - Sotto-elemento (indentazione può variare)
+ Altro tipo di bullet
* E un altro

#### Lista Numerata (H4)
1. Primo punto numerato.
2. Secondo punto con **grassetto**.
   Riga continua allineata.
10. Decimo punto per testare allineamento.

Testo normale alla fine. *Corsivo alla fine*. **Grassetto alla fine.** `Codice alla fine`.
"""

    print("\n--- Formatted Output (width=70) ---")
    print(TerminalFormatter.format_terminal_text(sample_text, width=70))

    print("\n--- Plain Text Output (width=70) ---")
    # Force disable ANSI for this test
    TerminalFormatter.enable_ansi(False)
    print(TerminalFormatter.format_terminal_text(sample_text, width=70))
    TerminalFormatter.enable_ansi(True) # Re-enable auto-detect

    print(f"\n{TerminalFormatter.BOLD}--- Test Finished ---{TerminalFormatter.RESET}")
