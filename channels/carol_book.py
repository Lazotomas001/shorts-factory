"""Full-length public-domain carols for the long-form Christmas channel.

Melodies/harmonies are LilyPond note strings. Hymn harmonies (SATB) come from public-domain
scores typeset by the Mutopia Project (mutopiaproject.org); the others are standard melodies.
Lyrics: one string per displayed line. Syllables are split with "-", "_" holds the previous
syllable over one more note (melisma). Every lyric and melody here was published before 1929.

Each song: parts (melody + harmony), and a form (which part, which verse, or None = instrumental).
"""

SONGS = {
    # ------------------------------------------------------------------ Silent Night
    "silent_night": {
        "title": "Silent Night", "credit": "Franz Gruber (1818), English words John F. Young (1859)",
        "bpm": 60, "feel": "hymn", "transpose": 0,
        "parts": {
            "verse": {
                "melody": "f'8. g'16 f'8 d'4. f'8. g'16 f'8 d'4. c''4 c''8 a'4. bes'4 bes'8 f'4. g'4 g'8 bes'8. a'16 g'8 f'8. g'16 f'8 d'4. g'4 g'8 bes'8. a'16 g'8 f'8. g'16 f'8 d'4. c''4 c''8 ees''8. c''16 a'8 bes'4. d'' bes'8. f'16 d'8 f'8. ees'16 c'8 bes2.",
                "satb": {
                    "alto": "d'8. ees'16 d'8 bes4. d'8. ees'16 d'8 bes4. ees'4 ees'8 c'4. d'4 d'8 d'4. ees'4 ees'8 g'8. f'16 ees'8 d'8. ees'16 d'8 bes4. ees'4 ees'8 g'8. f'16 ees'8 d'8. ees'16 d'8 bes4. ees'4 ees'8 a'8. ees'16 c'8 d'4. f' d'8. f'16 bes8 d'8. c'16 a8 bes2.",
                    "tenor": "bes4 bes8 f4. bes4 bes8 f4. a4 a8 f4. f4 f8 bes4. bes4 bes8 g8. a16 bes8 bes8. bes16 bes8 f4. bes4 bes8 g8. a16 bes8 bes8. bes16 bes8 f4. a4 a8 c'8. a16 f8 f4. bes bes4 f8 f8. f16 ees8 d2.",
                    "bass": "bes,4 bes,8 bes,4. bes,4 bes,8 bes,4. f4 f8 f4. bes,4 bes,8 bes,4. ees4 ees8 ees8. ees16 ees8 bes,8. bes,16 bes,8 bes,4. ees4 ees8 ees8. ees16 ees8 bes,8. bes,16 bes,8 bes,4. f4 f8 f8. f16 f8 bes,2. f4 f8 f,8. f,16 f,8 bes,2.",
                },
                "lines": [8, 6, 9, 9, 7, 7],
            },
        },
        "verses": {
            1: ["Si-lent night, _ ho-ly night! _", "All is calm, all is bright",
                "Round yon vir-gin moth-er and child _", "Ho-ly in-fant so ten-der and mild",
                "Sleep in heav-en-ly peace _", "Sleep in heav-en-ly _ peace."],
            2: ["Si-lent night, _ ho-ly night! _", "Shep-herds quake at the sight",
                "Glo-ries stream from heav-en a-far _", "Heav'n-ly hosts sing Al-le-lu-i-a",
                "Christ the Sav-ior is born _", "Christ the Sav-ior is _ born!"],
            3: ["Si-lent night, _ ho-ly night! _", "Son of God, love's pure light",
                "Ra-diant beams from Thy ho-ly face _", "With the dawn of re-deem-ing grace _",
                "Je-sus, Lord, at Thy birth _", "Je-sus, Lord, at Thy _ birth."],
        },
        "form": [("verse", 1), ("verse", 2), ("verse", None), ("verse", 3)],
    },
    # ------------------------------------------------------------------ O Come All Ye Faithful
    "o_come_all_ye_faithful": {
        "title": "O Come, All Ye Faithful", "credit": "John F. Wade (c. 1743), English words Frederick Oakeley (1841)",
        "bpm": 96, "feel": "hymn", "transpose": 0,
        "parts": {
            "verse": {
                "melody": "g'4 g'2 d'4 g' a'2 d' b'4 a' b' c'' b'2 a'4 g' g'2 fis'4 e' fis' g' a' b' fis'2 e'4. d'8 d'1 d''2 c''4 b' c''2 b' a'4 b' g' a' fis'4. e'8 d'4 b' b' a' b' c'' b'2 a'4 b' b' a' b' c'' b'2 a'4 b' c'' b' a' g' fis'2 g'4 c'' b'2 a'4. g'8 g'2.",
                "satb": {
                    "alto": "d'4 d'2 d'4 d' d'2 d' d'4 d' d' e' d'2 d'4 b b cis' d' cis' d'2 d'4 d' d'2 cis'4. d'8 d'1 d'2 e'8 fis' g'4 g' fis' g'2 d'4 d' e' e' d'2 d'4 b' b' a' b' c'' b'2 a'4 d' d' d' d' d' d'2 d'4 g' e'8 fis' g'4 d' d'8 cis' d'2 d'4 e' d'2 d'4. b8 b2.",
                    "tenor": "b4 b2 b4 b a2 a g4 a g g g2 fis4 g g2 a4 a a g fis e a2 g4. fis8 fis1 b2 c'4 d' c'2 d' a4 g b c' a4. g8 fis4 r r1 r2. g4 g fis g a g2 fis4 d' c' d' a a a2 g4 g g2 fis4. g8 g2.",
                    "bass": "g4 g2 b4 g fis2 fis g4 fis g c d2 d4 e e2 d4 a, d b, fis, g, a,2 a,4. d8 d1 b2 a4 g a2 g fis4 g e c d2 d4 r r1 r2. g4 g fis g a g2 fis4 g a g fis e d c b, c d2 d4. g,8 g,2.",
                },
                "lines": [12, 12, 12, 7, 7, 12],
            },
        },
        "verses": {
            1: ["O come, all ye faith-ful, joy-ful and tri-um-phant,", "O come ye, O come ye to Beth-le-hem; _ _",
                "Come and be-hold Him, born the King of an- _ gels;", "O come, let us a-dore Him,",
                "O come, let us a-dore Him,", "O come, let us a-dore Him, Christ the Lord. _ _"],
            2: ["Sing, choirs of an- _ gels, sing in ex-ul-ta-tion;", "Sing, all ye cit-i-zens of heav'n a-bove! _ _",
                "Glo-ry to God, all glo-ry in the high- _ est;", "O come, let us a-dore Him,",
                "O come, let us a-dore Him,", "O come, let us a-dore Him, Christ the Lord. _ _"],
            3: ["Yea, Lord, we greet _ Thee, born this hap-py morn-ing;", "Je-sus, to Thee be all glo-ry giv'n; _ _ _",
                "Word of the Fa-ther, now in flesh ap-pear- _ ing;", "O come, let us a-dore Him,",
                "O come, let us a-dore Him,", "O come, let us a-dore Him, Christ the Lord. _ _"],
        },
        "form": [("verse", 1), ("verse", 2), ("verse", 3)],
    },
    # ------------------------------------------------------------------ Good King Wenceslas
    "good_king_wenceslas": {
        "title": "Good King Wenceslas", "credit": "Words John Mason Neale (1853), tune Piae Cantiones (1582)",
        "bpm": 116, "feel": "hymn", "transpose": -2,
        "parts": {
            "verse": {
                "melody": "a4 a a b a a e2 fis4 e fis gis a2 a2 a4 a a b a a e2 fis4 e fis gis a2 a2 e'4 d cis b cis b a2 fis4 e fis gis a2 a2 e4 e fis gis a a b2 e4 d cis b a2( d) a1",
                "relative": "a'",
                "satb": {
                    "alto": "e4 e fis e e fis b,2 d4 e d d e2 e2 e4 e fis e e fis b,2 d4 e d d e2 e2 a4 a4 a4 gis a gis fis2 a,4 e' d d e2 e e4 e d d cis cis e2 e4 a a gis a2( fis) e1",
                    "tenor": "cis4 cis cis b cis d gis,2 a4 a a b cis2 cis2 cis4 cis cis b cis d gis,2 a4 a a b cis2 cis2 e4 fis e e e e cis2 d4 a a b cis2 cis a4 a a b a a gis2 a4 fis' e e cis2( d) cis1",
                    "bass": "a4 a fis gis a d, e2 d4 cis d b a2 a2 a'4 a fis gis a d, e2 d4 cis d b a2 a2 cis4 d e e a e fis2 d4 cis d b a2 a2 cis4 cis d b fis' fis e2 cis4 d e e fis2( d) a'1",
                    "relative": {"alto": "a'", "tenor": "a", "bass": "a"},
                },
                "lines": [13, 13, 13, 14],
            },
        },
        "verses": {
            1: ["Good King Wen-ces-las looked out on the feast of Ste-phen,", "When the snow lay round a-bout, deep and crisp and e-ven;",
                "Bright-ly shone the moon that night, though the frost was cru-el,", "When a poor man came in sight, gath-'ring win-ter fu- _ el."],
            2: ["\"Hith-er, page, and stand by me, if thou know'st it, tell-ing,", "Yon-der peas-ant, who is he? Where and what his dwell-ing?\"",
                "\"Sire, he lives a good league hence, un-der-neath the moun-tain,", "Right a-gainst the for-est fence, by Saint Ag-nes' foun- _ tain.\""],
            3: ["\"Bring me flesh and bring me wine, bring me pine logs hith-er;", "Thou and I will see him dine, when we bear them thith-er.\"",
                "Page and mon-arch forth they went, forth they went to-geth-er,", "Through the rude wind's wild la-ment and the bit-ter weath- _ er."],
            4: ["\"Sire, the night is dark-er now, and the wind blows strong-er;", "Fails my heart, I know not how; I can go no long-er.\"",
                "\"Mark my foot-steps, good my page, tread thou in them bold-ly;", "Thou shalt find the win-ter's rage freeze thy blood less cold- _ ly.\""],
            5: ["In his mas-ter's steps he trod, where the snow lay dint-ed;", "Heat was in the ver-y sod which the saint had print-ed.",
                "There-fore, Chris-tian men, be sure, wealth or rank pos-sess-ing,", "Ye who now will bless the poor shall your-selves find bless- _ ing."],
        },
        "form": [("verse", 1), ("verse", 2), ("verse", 3), ("verse", None), ("verse", 4), ("verse", 5)],
    },
    # ------------------------------------------------------------------ Jingle Bells
    "jingle_bells": {
        "title": "Jingle Bells", "credit": "James Lord Pierpont (1857)",
        "bpm": 138, "feel": "bells", "transpose": 0,
        "parts": {
            "verse": {
                "melody": "g'4 e'' d'' c'' g'2. g'8 g'8 g'4 e'' d'' c'' a'1 a'4 f'' e'' d'' b'1 g''4 g'' f'' d'' e''1 g'4 e'' d'' c'' g'1 g'4 e'' d'' c'' a'2. a'4 a'4 f'' e'' d'' g''4 g'' g''4. g''8 a''4 g'' f'' d'' c''2 g''2",
                "chords": [(4, c) for c in "C C C F F G G7 C C C C F F C G7 C".split()],
                "lines": [12, 10, 10, 15],
            },
            "chorus": {
                "melody": "e''4 e'' e''2 e''4 e'' e''2 e''4 g'' c''4. d''8 e''1 f''4 f'' f''4. f''8 f''4 e'' e'' e''8 e''8 e''4 d'' d'' e'' d''2 g''2 e''4 e'' e''2 e''4 e'' e''2 e''4 g'' c''4. d''8 e''1 f''4 f'' f''4. f''8 f''4 e'' e'' e''8 e''8 g''4 g'' f'' d'' c''1",
                "chords": [(4, c) for c in "C C C C F C D7 G C C C C F C G7 C".split()],
                "lines": [11, 15, 11, 14],
            },
        },
        "verses": {
            "v1": ["Dash-ing through the snow in a one=horse o-pen sleigh,", "O'er the fields we go, laugh-ing all the way;",
                   "Bells on bob-tail ring, mak-ing spir-its bright;", "What fun it is to ride and sing a sleigh-ing song to-night! Oh!"],
            "ch": ["Jin-gle bells, jin-gle bells, jin-gle all the way!", "Oh, what fun it is to ride in a one=horse o-pen sleigh, hey!",
                   "Jin-gle bells, jin-gle bells, jin-gle all the way!", "Oh, what fun it is to ride in a one=horse o-pen sleigh!"],
        },
        "form": [("verse", "v1"), ("chorus", "ch"), ("verse", None), ("chorus", "ch"), ("chorus", "ch")],
    },
    # ------------------------------------------------------------------ Deck the Halls
    "deck_the_halls": {
        "title": "Deck the Halls", "credit": "Welsh tune 'Nos Galan', English words (1862)",
        "bpm": 120, "feel": "bells", "transpose": -2,
        "parts": {
            "verse": {
                "melody": ("g''4. f''8 e''4 d'' c'' d'' e'' c'' d''8 e'' f'' d'' e''4. d''8 c''4 b' c''2 "
                           "g''4. f''8 e''4 d'' c'' d'' e'' c'' d''8 e'' f'' d'' e''4. d''8 c''4 b' c''2 "
                           "d''4. e''8 f''4 d'' e''4. f''8 g''4 d'' e''8 fis'' g''4 a''8 b'' c'''4 b'' a'' g''2 "
                           "g''4. f''8 e''4 d'' c'' d'' e'' c'' a''8 a'' a'' a'' g''4. f''8 e''4 d'' c''2"),
                "chords": ([(4, "C"), (4, "C"), (4, "G7"), (4, "C")] * 2 +
                           [(4, "G7"), (2, "C"), (2, "G"), (2, "G"), (2, "D7"), (4, "G")] +
                           [(4, "C"), (4, "C"), (2, "F"), (2, "C"), (2, "G7"), (2, "C")]),
                "lines": [17, 17, 17, 17],
            },
        },
        "verses": {
            1: ["Deck the halls with boughs of hol-ly, fa la la la la, la la la la!", "'Tis the sea-son to be jol-ly, fa la la la la, la la la la!",
                "Don we now our gay ap-par-el, fa la la, la la la, la la la!", "Troll the an-cient Yule-tide car-ol, fa la la la la, la la la la!"],
            2: ["See the blaz-ing Yule be-fore us, fa la la la la, la la la la!", "Strike the harp and join the cho-rus, fa la la la la, la la la la!",
                "Fol-low me in mer-ry mea-sure, fa la la, la la la, la la la!", "While I tell of Yule-tide trea-sure, fa la la la la, la la la la!"],
            3: ["Fast a-way the old year pass-es, fa la la la la, la la la la!", "Hail the new, ye lads and lass-es, fa la la la la, la la la la!",
                "Sing we joy-ous, all to-geth-er, fa la la, la la la, la la la!", "Heed-less of the wind and weath-er, fa la la la la, la la la la!"],
        },
        "form": [("verse", 1), ("verse", 2), ("verse", None), ("verse", 3)],
    },
    # ------------------------------------------------------------------ We Wish You a Merry Christmas
    "we_wish_you": {
        "title": "We Wish You a Merry Christmas", "credit": "Traditional English (West Country)",
        "bpm": 132, "feel": "bells", "transpose": 0,
        "parts": {
            "verse": {
                "melody": "g'4 c''4 c''8 d'' c'' b' a'4 a' a' d''4 d''8 e'' d'' c'' b'4 g' g' e''4 e''8 f'' e'' d'' c''4 a' g'8 g' a'4 d'' b' c''2.",
                "chords": [(1, "N"), (3, "C"), (3, "F"), (3, "D7"), (3, "G"), (3, "E7"), (3, "Am"), (1, "F"), (2, "G"), (3, "C")],
                "lines": [8, 8, 8, 6],
            },
        },
        "verses": {
            1: ["We wish you a mer-ry Christ-mas,", "We wish you a mer-ry Christ-mas,", "We wish you a mer-ry Christ-mas", "And a hap-py New Year!"],
            2: ["Oh, bring us some fig-gy pud-ding,", "Oh, bring us some fig-gy pud-ding,", "Oh, bring us some fig-gy pud-ding,", "And _ bring some out here!"],
            3: ["We won't go un-til we get some,", "We won't go un-til we get some,", "We won't go un-til we get some,", "So _ bring some out here!"],
            4: ["We all like our fig-gy pud-ding,", "We all like our fig-gy pud-ding,", "We all like our fig-gy pud-ding,", "With _ all its good cheer!"],
        },
        "form": [("verse", 1), ("verse", 2), ("verse", 3), ("verse", None), ("verse", 4), ("verse", 1)],
    },
}
