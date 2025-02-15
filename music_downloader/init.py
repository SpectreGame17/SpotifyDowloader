import os
import re

def clear_terminal():
    """Pulisce il terminale a seconda del sistema operativo."""
    if os.name == 'nt':  # Windows
        os.system('cls')
    else:
        os.system('clear')

def sanitize_filename(name):
    """Rimuove i caratteri non ammessi dal nome e pulisce il risultato."""
    return re.sub(r'[\/:*?."<>|]', " ", name).strip().rstrip('.')
