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
            if not cls._ansi_enabled: # Try to enable it if on Windows and not explicitly supported by env vars
                os.system('') # This call can activate VT100 processing in some Windows consoles
                # We don't re-check here as it's a one-shot attempt; subsequent calls will use the initial detection.
        else:
            # Unix-like check (stdout is a TTY)
            # Also check TERM environment variable for common values
            term = os.environ.get('TERM', '')
            cls._ansi_enabled = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and \
                                ('xterm' in term or 'screen' in term or 'vt100' in term or 'linux' in term or 'alacritty' in term or 'kitty' in term)
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
        # in_code_block = False # Basic state for potential future ```code block``` handling

        # Split lines but preserve trailing newline if present
        lines = text.splitlines() # Handles different newline types

        for line_idx, line_content in enumerate(lines):
            original_line = line_content # For fallback/debugging

            # --- Block Element Formatting (Applied first) ---
            processed_block = False

            # Headings
            heading_match = re.match(cls.RE_HEADING, line_content)
            if heading_match:
                level = len(heading_match.group(1))
                content = heading_match.group(2).strip()
                formatted_lines.append(cls.format_heading(content, level))
                processed_block = True

            # Blockquotes (apply dim/italic style)
            elif re.match(cls.RE_QUOTE, line_content):
                m = re.match(cls.RE_QUOTE, line_content)
                # Recursively format the quote content for inline styles
                quote_content_styled = cls.format_inline_styles(m.group(1))
                # Apply wrapping to the quote content *after* inline formatting
                # Indent by 2 for the "> " part
                wrapped_quote_lines = textwrap.wrap(quote_content_styled, width=effective_width - 2, subsequent_indent='  ')
                for wq_line_idx, wq_line_content in enumerate(wrapped_quote_lines):
                    if wq_line_idx == 0:
                        formatted_lines.append(f"{cls.DIM}{cls.ITALIC}{cls.CYAN}> {wq_line_content}{cls.RESET}")
                    else: # Subsequent lines of a wrapped quote are already indented by textwrap
                        formatted_lines.append(f"{cls.DIM}{cls.ITALIC}{cls.CYAN}{wq_line_content}{cls.RESET}")
                processed_block = True

            # Bullet Lists (apply color and bullet)
            elif re.match(cls.RE_BULLET_LIST, line_content):
                m = re.match(cls.RE_BULLET_LIST, line_content)
                bullet = m.group(1)
                item_content_styled = cls.format_inline_styles(m.group(2))
                # Indent for "  * " prefix. Subsequent lines should align with item_content.
                wrapped_item_lines = textwrap.wrap(item_content_styled, width=effective_width - 4, subsequent_indent='    ')
                for wi_line_idx, wi_line_content in enumerate(wrapped_item_lines):
                    if wi_line_idx == 0:
                        formatted_lines.append(f"{cls.YELLOW}  {bullet} {cls.RESET}{wi_line_content}")
                    else: # Already indented by textwrap subsequent_indent
                        formatted_lines.append(f"{cls.RESET}{wi_line_content}") # Reset needed if previous line ended with color
                processed_block = True

            # Numbered Lists
            elif re.match(cls.RE_NUMBER_LIST, line_content):
                m = re.match(cls.RE_NUMBER_LIST, line_content)
                number = m.group(1)
                item_content_styled = cls.format_inline_styles(m.group(2))
                # Adjust indent for " 1. " (number length + ". ")
                num_prefix_len = len(number) + 2
                sub_indent = ' ' * (num_prefix_len + 1) # Subsequent indent for wrapped lines
                wrapped_item_lines = textwrap.wrap(item_content_styled, width=effective_width - (num_prefix_len+1), subsequent_indent=sub_indent)
                for wi_line_idx, wi_line_content in enumerate(wrapped_item_lines):
                    if wi_line_idx == 0:
                        formatted_lines.append(f"{cls.YELLOW} {number}. {cls.RESET}{wi_line_content}")
                    else: # Already indented
                         formatted_lines.append(f"{cls.RESET}{wi_line_content}")
                processed_block = True


            # --- Inline Formatting and Wrapping (if not a processed block element) ---
            if not processed_block:
                # Apply inline styles first
                formatted_line_content = cls.format_inline_styles(line_content)

                # Wrap the line after inline styles are applied
                try:
                    # Handle empty lines correctly (textwrap returns empty list for empty string)
                    wrapped_sub_lines = textwrap.wrap(formatted_line_content, width=effective_width) if formatted_line_content.strip() else ['']
                    formatted_lines.extend(wrapped_sub_lines)
                except Exception as e:
                    # Fallback if wrapping fails (e.g., complex ANSI sequences miscalculated by textwrap)
                    # print(f"{cls.RED}Warning: Text wrapping failed for line: {original_line} (Error: {e}){cls.RESET}", file=sys.stderr)
                    formatted_lines.append(original_line) # Append original line on error

        return '\n'.join(formatted_lines)

    @classmethod
    def format_inline_styles(cls, line: str) -> str:
        """Applies inline formatting (bold, italic, etc.) using regex."""
        # Apply styles in a specific order to avoid conflicts (e.g., bold first)
        line = re.sub(cls.RE_BOLD_STARS, f"{cls.BOLD}\\1{cls.RESET_BOLD}", line, flags=re.DOTALL)
        line = re.sub(cls.RE_BOLD_UNDERSCORES, f"{cls.BOLD}\\1{cls.RESET_BOLD}", line, flags=re.DOTALL)
        line = re.sub(cls.RE_ITALIC_STARS, f"{cls.ITALIC}\\1{cls.RESET_ITALIC}", line, flags=re.DOTALL)
        line = re.sub(cls.RE_ITALIC_UNDERSCORES, f"{cls.ITALIC}\\1{cls.RESET_ITALIC}", line, flags=re.DOTALL)
        line = re.sub(cls.RE_UNDERLINE, f"{cls.UNDERLINE}\\1{cls.RESET_UNDERLINE}", line, flags=re.DOTALL)
        line = re.sub(cls.RE_HIGHLIGHT, f"{cls.REVERSE}\\1{cls.RESET_REVERSE}", line, flags=re.DOTALL)
        return line

    # Helper properties for resetting specific styles if we want to be granular
    # This helps if styles are nested, though full proper nesting is hard with regex.
    # For simple cases, just RESET is fine.
    @classmethod
    @property
    def RESET_BOLD(cls): return cls.RESET # Or specific un-bold if terminal supports and it's needed
    @classmethod
    @property
    def RESET_ITALIC(cls): return cls.RESET
    @classmethod
    @property
    def RESET_UNDERLINE(cls): return cls.RESET
    @classmethod
    @property
    def RESET_REVERSE(cls): return cls.RESET


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
            line = re.sub(r'\*\*(.+?)\*\*', r'\1', line, flags=re.DOTALL)
            line = re.sub(r'__(.+?)__', r'\1', line, flags=re.DOTALL)
            line = re.sub(r'(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])', r'\1', line, flags=re.DOTALL)
            line = re.sub(r'(?<![\w_])_(?!_)(.+?)(?<!_)_(?![\w_])', r'\1', line, flags=re.DOTALL)
            line = re.sub(r'~(.*?)~', r'\1', line, flags=re.DOTALL)
            line = re.sub(r'`(.*?)`', r'\1', line, flags=re.DOTALL)

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
if __name__ == '__main__':
    print(f"{TerminalFormatter.BOLD}--- Terminal ANSI Support Test ---{TerminalFormatter.RESET}")
    if TerminalFormatter.supports_ansi():
        print(f"{TerminalFormatter.GREEN}✓ ANSI support detected/enabled.{TerminalFormatter.RESET}")
    else:
        if os.name == 'nt':
            os.system('')
            if TerminalFormatter.supports_ansi():
                print(f"{TerminalFormatter.YELLOW}✓ ANSI support enabled (likely via OS trick).{TerminalFormatter.RESET}")
                TerminalFormatter.enable_ansi(True) # Explicitly enable if trick worked
            else:
                print(f"{TerminalFormatter.RED}⚠ ANSI support not detected. Formatting will be plain text.{TerminalFormatter.RESET}")
        else:
            print(f"{TerminalFormatter.RED}⚠ ANSI support not detected. Formatting will be plain text.{TerminalFormatter.RESET}")

    print(f"\n{TerminalFormatter.BOLD}--- Visual Formatting Test ---{TerminalFormatter.RESET}")
    sample_text = """# Intestazione Livello 1
Questo è testo normale sotto H1. Contiene **grassetto**, *corsivo*, ~sottolineato~ e `codice inline`. _Anche underscore italici_. __E bold__.
Un'altra riga di testo **con grassetto che si estende\nsu più righe** per testare DOTALL.
*E corsivo che\nva a capo anche lui.*

## Intestazione Livello 2 con `codice`
Paragrafo dopo H2.
> Questo è un blocco citazione.
> Può contenere **formattazione** *inline* e si estende su più righe,
> sperando che il wrapping funzioni correttamente con l'indentazione e mantenga lo stile.
> Ultima riga della citazione.

### Lista Puntata (H3)
- Primo elemento molto lungo che dovrebbe andare a capo correttamente mantenendo l'allineamento del testo successivo sotto il bullet e non sotto il simbolo del bullet.
- Secondo con *corsivo*
  - Sotto-elemento (indentazione può variare, qui non gestita specificamente)
+ Altro tipo di bullet con testo che si spera vada a capo bene.
* E un altro.

#### Lista Numerata (H4)
1. Primo punto numerato, anche questo abbastanza lungo per vedere come gestisce il wrapping delle righe successive.
2. Secondo punto con **grassetto**.
   Riga continua allineata manualmente (questo non è wrapping automatico).
10. Decimo punto per testare allineamento con numeri a due cifre. Questo testo è anche lungo per vedere il wrapping.

Testo normale alla fine. *Corsivo alla fine*. **Grassetto alla fine.** `Codice alla fine`.
Un'ultima riga normale.
"""

    print("\n--- Formatted Output (width=70) ---")
    # Ensure ANSI is enabled for this part of the test if auto-detection was tricky
    # TerminalFormatter.enable_ansi(True)
    print(TerminalFormatter.format_terminal_text(sample_text, width=70))

    print("\n--- Plain Text Output (width=70) ---")
    TerminalFormatter.enable_ansi(False) # Force disable ANSI for this test
    print(TerminalFormatter.format_terminal_text(sample_text, width=70))
    # Re-enable based on detection for subsequent runs or other scripts importing this
    TerminalFormatter._ansi_enabled = None # Reset to allow re-detection next time supports_ansi is called

    print(f"\n{TerminalFormatter.BOLD}--- Test Finished ---{TerminalFormatter.RESET}")
