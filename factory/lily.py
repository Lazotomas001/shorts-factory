"""Minimal LilyPond note reader (enough for public-domain hymn/carol scores from the Mutopia Project).

parse("g'4 g'2 d'4 ( e'8 ) fis'4. r4", relative=None) -> list of Note
Supports: absolute or \\relative pitches, is/es accidentals, ' and , octave marks, durations with dots,
rests (r) / spacers (s), slurs ( ), ties ~, bar checks |. Other commands are ignored.
"""
import re
from dataclasses import dataclass

STEP = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
LETTER_IDX = {"c": 0, "d": 1, "e": 2, "f": 3, "g": 4, "a": 5, "b": 6}


@dataclass
class Note:
    midi: int | None      # None = rest
    beats: float          # quarter-note beats
    slur_cont: bool = False   # this note continues the previous syllable (inside a slur or tied)


TOKEN = re.compile(r"\\[a-zA-Z]+|\"[^\"]*\"|[a-gsr](?:is|es|s)*[',]*=?[',]*\d*\.*|[()~|{}<>]|\S+")


def _pitch(tok):
    m = re.match(r"([a-g])((?:is|es|s)*)([',]*)", tok)
    letter, acc, octs = m.groups()
    alt = acc.count("is") - acc.count("es") - (1 if acc == "s" else 0)
    up = octs.count("'") - octs.count(",")
    return letter, alt, up


def parse(src: str, relative: str | None = None):
    src = re.sub(r"%.*", "", src)
    toks = TOKEN.findall(src)
    notes, dur, in_slur, tie_next = [], 1.0, False, False
    prev_letter, prev_midi = None, None
    if relative:
        l, a, u = _pitch(relative)
        prev_letter, prev_midi = l, 48 + STEP[l] + a + 12 * u  # c = C3 in LilyPond
    skip_next = False
    for t in toks:
        if skip_next:
            skip_next = False
            continue
        if t.startswith("\\"):
            if t in ("\\partial", "\\time", "\\key", "\\bar", "\\tempo", "\\clef"):
                skip_next = t in ("\\partial", "\\time", "\\bar", "\\clef")
            continue
        if t == "(":
            in_slur = True
            continue
        if t == ")":
            in_slur = False
            continue
        if t == "~":
            tie_next = True
            continue
        if t in "|{}<>" or t.startswith('"'):
            continue
        m = re.match(r"([a-gsr](?:is|es|s)*)([',]*)=?[',]*(\d*)(\.*)$", t)
        if not m:
            continue
        name, octs, d, dots = m.groups()
        if d:
            base = 4.0 / int(d)
            dur = base * (2 - 0.5 ** len(dots)) if dots else base
        elif dots:
            pass
        if name in ("r", "s"):
            notes.append(Note(None, dur))
            tie_next = False
            continue
        letter, alt, _ = _pitch(name + octs)
        up = octs.count("'") - octs.count(",")
        if relative and prev_letter is not None:
            # closest octave to previous note (by letter distance), then apply marks
            diff = LETTER_IDX[letter] - LETTER_IDX[prev_letter]
            if diff > 3:
                diff -= 7
            elif diff < -3:
                diff += 7
            target_idx = LETTER_IDX[prev_letter] + diff
            prev_oct = (prev_midi - STEP[prev_letter]) // 12
            octave = prev_oct + (target_idx // 7)
            midi = 12 * octave + STEP[letter] + alt + 12 * up
            prev_letter, prev_midi = letter, 12 * octave + STEP[letter] + 12 * up
        else:
            midi = 48 + STEP[letter] + alt + 12 * up
        cont = in_slur or tie_next   # LilyPond: "(" follows the first note of a slur
        n = Note(midi, dur, slur_cont=bool(cont))
        if tie_next and notes and notes[-1].midi == midi:
            notes[-1].beats += dur      # merge tie into one longer note
            tie_next = False
            continue
        tie_next = False
        notes.append(n)
    return notes
