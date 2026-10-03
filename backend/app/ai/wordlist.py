"""Warstwa 1 moderacji: szybka lokalna lista polskich wulgaryzmów (bez wołania LLM).

Lista to rdzenie słów; dopasowanie po normalizacji (małe litery, bez polskich znaków,
zamiana „leetspeak”, usunięcie powtórzeń i separatorów wewnątrz słowa).
"""

import re
import unicodedata

# Rdzenie (po normalizacji). Celowo krótka, rozsądna lista na MVP.
ROOTS = [
    "kurw", "kurew", "chuj", "huj", "chuja", "pierdol", "pierdal", "jeban", "jebac", "jebie", "jebn",
    "zajeb", "wyjeb", "pojeb", "spierdal", "wypierdal", "skurwys", "skurwiel", "pizd", "cipa", "cipk",
    "kutas", "fiut", "dziwk", "suka", "debil", "idiot", "kretyn", "cwel", "zjeb",
    "fuck", "shit", "bitch",
]
# Słowa, które zawierają rdzeń, a są niewinne.
ALLOW = {"suknia", "sukienka", "sukces", "sukcesy", "sukcesu", "huba", "hubert", "hujawa"}

LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i"})


def _strip_accents(s: str) -> str:
    s = s.replace("ł", "l").replace("Ł", "L")
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalize(text: str) -> list[str]:
    t = _strip_accents(text.lower()).translate(LEET)
    # k*u*r*w*a, k.u.r.w.a, k u r w a → łączymy pojedyncze litery rozdzielone separatorami
    t = re.sub(r"\b(?:\w[\s.*_\-]){2,}\w\b", lambda m: re.sub(r"[\s.*_\-]", "", m.group(0)), t)
    t = re.sub(r"[*_\-.]", "", t)
    t = re.sub(r"(.)\1{2,}", r"\1", t)  # kuuuurwa → kurwa
    return re.findall(r"[a-z]+", t)


def find_profanity(text: str) -> list[str]:
    hits = []
    for word in normalize(text):
        if word in ALLOW:
            continue
        variants = {word, word.replace("ch", "h")}
        if any(v.startswith(r) or (len(r) >= 5 and r in v) for v in variants for r in ROOTS):
            hits.append(word)
    return hits
