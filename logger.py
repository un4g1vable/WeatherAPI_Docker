from colorama import Fore, Style, init

init(autoreset=True)

def log(source: str, message: str):
    colors = {
        "http": Fore.CYAN,
        "parser": Fore.GREEN,
        "db": Fore.BLUE,
        "system": Fore.WHITE,
        "error": Fore.RED,
    }
    color = colors.get(source.lower(), Fore.WHITE)
    print(f"{color}[{source.upper()}] {message}{Style.RESET_ALL}")