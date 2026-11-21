"""Public-domain Christmas carols (melody + lyrics published before 1929).

Format per note: (pitch, beats, syllable). A syllable ending in "-" continues the word;
"~" means the previous syllable is held across this note. Chords: (beats, name).
All recordings are synthesized by this project, so there is no recording copyright.
Add more songs by following the same format (only use pre-1929 lyrics + melodies).
"""


def _line(spec):
    out = []
    for tok in spec.split():
        p, b, s = tok.split("|")
        out.append((p, float(b), s.replace("_", " ")))
    return out


JB1 = _line("E5|1|Jin- E5|1|gle E5|2|bells, E5|1|jin- E5|1|gle E5|2|bells, E5|1|jin- G5|1|gle C5|1.5|all D5|.5|the E5|4|way!")
JB2 = _line("F5|1|Oh F5|1|what F5|1.5|fun F5|.5|it F5|1|is E5|1|to E5|1|ride E5|.5|in E5|.5|a E5|1|one= D5|1|horse D5|1|o- E5|1|pen D5|2|sleigh, G5|2|hey!")
JB4 = _line("F5|1|Oh F5|1|what F5|1.5|fun F5|.5|it F5|1|is E5|1|to E5|1|ride E5|.5|in E5|.5|a G5|1|one= G5|1|horse F5|1|o- D5|1|pen C5|4|sleigh!")

FALA = "D5|.5|Fa E5|.5|la F5|.5|la D5|.5|la E5|1.5|la, D5|.5|la C5|1|la B4|1|la C5|2|la!"
DH1 = _line("G5|1.5|Deck F5|.5|the E5|1|halls D5|1|with C5|1|boughs D5|1|of E5|1|hol- C5|1|ly, " + FALA)
DH2 = _line("G5|1.5|'Tis F5|.5|the E5|1|sea- D5|1|son C5|1|to D5|1|be E5|1|jol- C5|1|ly, " + FALA)
DH3 = _line("D5|1.5|Don E5|.5|we F5|1|now D5|1|our E5|1.5|gay F5|.5|ap- G5|1|par- D5|1|el, "
            "E5|.5|Fa F#5|.5|la G5|1|la, A5|.5|la B5|.5|la C6|1|la, B5|1|la A5|1|la G5|2|la!")
DH4 = _line("G5|1.5|Troll F5|.5|the E5|1|an- D5|1|cient C5|1|Yule- D5|1|tide E5|1|car- C5|1|ol, "
            "A5|.5|Fa A5|.5|la A5|.5|la A5|.5|la G5|1.5|la, F5|.5|la E5|1|la D5|1|la C5|2|la!")


def _ww(a, b, c, last):
    # three 8-syllable lines + closing line on the same tune
    w1 = [s for s in a.split()]
    w2 = [s for s in b.split()]
    w3 = [s for s in c.split()]
    l1 = _line(" ".join(f"{p}|{d}|{s}" for (p, d), s in zip(
        [("G4", 1), ("C5", 1), ("C5", .5), ("D5", .5), ("C5", .5), ("B4", .5), ("A4", 1), ("A4", 1)], w1)))
    l2 = _line(" ".join(f"{p}|{d}|{s}" for (p, d), s in zip(
        [("A4", 1), ("D5", 1), ("D5", .5), ("E5", .5), ("D5", .5), ("C5", .5), ("B4", 1), ("G4", 1)], w2)))
    l3 = _line(" ".join(f"{p}|{d}|{s}" for (p, d), s in zip(
        [("G4", 1), ("E5", 1), ("E5", .5), ("F5", .5), ("E5", .5), ("D5", .5), ("C5", 1), ("A4", 1)], w3)))
    return [l1, l2, l3, _line(last)]


WW_WISH = "We wish you a mer- ry Christ- mas,"
WW_FIG = "Oh, bring us some fig- gy pud- ding,"
WW_WONT = "We won't go un- til we get some,"
WW_CH = ([(1, "N")] + [(3, c) for c in ("C", "F", "D7", "G", "E7", "Am")] + [(1, "F"), (2, "G"), (3, "C")])

SN = [
    _line("G4|1.5|Si- A4|.5|lent G4|1|night, E4|3|~ G4|1.5|ho- A4|.5|ly G4|1|night, E4|3|~"),
    _line("D5|2|All D5|1|is B4|3|calm, C5|2|all C5|1|is G4|3|bright"),
    _line("A4|2|Round A4|1|yon C5|1.5|vir- B4|.5|gin A4|1|moth- G4|1.5|er A4|.5|and G4|1|child, E4|3|~"),
    _line("A4|2|Ho- A4|1|ly C5|1.5|in- B4|.5|fant A4|1|so G4|1.5|ten- A4|.5|der G4|1|and E4|3|mild,"),
    _line("D5|2|Sleep D5|1|in F5|1.5|heav- D5|.5|en- B4|1|ly C5|3|peace, E5|3|~"),
    _line("C5|1.5|Sleep G4|.5|in E4|1|heav- G4|1.5|en- F4|.5|ly D4|1|~ C4|6|peace."),
]

SONGS = {
    "jingle_bells": {
        "title": "Jingle Bells", "year": "1857", "bpm": 132, "meter": 4, "bells": True,
        "sections": [[JB1, JB2, JB1, JB4]],
        "chords": [[(4, c) for c in "C C C C F C D7 G C C C C F C G7 C".split()]],
        "repeat_faster": True,
    },
    "deck_the_halls": {
        "title": "Deck the Halls", "year": "1862", "bpm": 118, "meter": 4, "bells": True,
        "sections": [[DH1, DH2, DH3, DH4]],
        "chords": [[(4, "C"), (4, "C"), (4, "G7"), (4, "C")] * 2 +
                   [(4, "G7"), (2, "C"), (2, "G"), (2, "G"), (2, "D7"), (4, "G")] +
                   [(4, "C"), (4, "C"), (2, "F"), (2, "C"), (2, "G7"), (2, "C")]],
    },
    "we_wish_you": {
        "title": "We Wish You a Merry Christmas", "year": "trad. 16th c.", "bpm": 160, "meter": 3, "bells": True,
        "sections": [
            _ww(WW_WISH, WW_WISH, WW_WISH, "G4|.5|And G4|.5|a A4|1|hap- D5|1|py B4|1|New C5|3|Year!"),
            _ww(WW_FIG, WW_FIG, WW_FIG, "G4|1|So A4|1|bring D5|1|some B4|1|out C5|3|here!"),
            _ww(WW_WONT, WW_WONT, WW_WONT, "G4|1|So A4|1|bring D5|1|some B4|1|out C5|3|here!"),
            _ww(WW_WISH, WW_WISH, WW_WISH, "G4|.5|And G4|.5|a A4|1|hap- D5|1|py B4|1|New C5|3|Year!"),
        ],
        "chords": [WW_CH] * 4,
    },
    "silent_night": {
        "title": "Silent Night", "year": "1818 / English 1859", "bpm": 92, "meter": 3, "bells": False,
        "sections": [SN],
        "chords": [[(3, c) for c in "C C C C G7 G7 C C F F C C F F C C G7 G7 C C C G7 C C".split()]],
    },
}
