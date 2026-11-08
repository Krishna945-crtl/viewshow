"""Vocabulary for the theme engine.

Kept apart from the engine so tuning a look never touches scoring code.
Each archetype is a visual family (palette + particles + ambience) plus the
words that point to it. Words are stemmed at import, so "monsters" == "monster".
Multi-word phrases use "_" ("deep_sea", "red_sandalwood").
"""

from __future__ import annotations


def _a(primary, secondary, accent, particles, sound, fog, pulse, mood, label, words):
    return {"primary": primary, "secondary": secondary, "accent": accent, "particles": particles,
            "sound": sound, "fog": fog, "pulse": pulse, "mood": mood, "label": label, "words": words.split()}


# primary = dominant light, secondary = deep supporting wash, accent = highlights / particles
ARCHETYPES: dict[str, dict] = {
    "desert": _a("#c8862f", "#6a3d17", "#f2c46b", "sand", "desert_wind", 0.02, 0.15, "warm desert haze", "Desert",
                 "desert dune sand spice nomad oasis pharaoh mirage sahara camel caravan bedouin drought "
                 "dust scorching egypt pyramid cowboy outlaw sheriff frontier ranch gunslinger canyon arid"),
    "wasteland": _a("#d0642b", "#2e1d14", "#4cc3c9", "sand", "desert_wind", 0.028, 0.2, "scorched wasteland",
                    "Wasteland",
                    "apocalypse apocalyptic post_apocalyptic wasteland dystopia dystopian ruin scavenger survivor "
                    "fallout nuclear radiation collapse barren warlord war_rig mutant rust"),
    "ocean": _a("#1e6fd9", "#0a2a5c", "#5fd4ff", "bubbles", "deep_ocean", 0.03, 0.35, "abyssal blue", "Ocean",
                "ocean sea deep_sea underwater water wave reef tide tsunami whale shark kaiju titan atlantis "
                "submarine diver diving coral island ship shipwreck sailor pirate voyage mermaid aquatic lagoon "
                "harbor harbour coast coastal marine abyss storm iceberg"),
    "sky": _a("#f0a24a", "#12304f", "#8fd0ff", "mist", "desert_wind", 0.016, 0.2, "golden-hour skies", "Sky",
              "pilot aviator jet fighter_jet flight sky aircraft airplane plane cockpit squadron wing airline cloud "
              "flying fly parachute balloon altitude supersonic airbase dogfight runway"),
    "cosmic": _a("#6c5ce7", "#141a3d", "#a5f3fc", "stars", "space_hum", 0.012, 0.25, "deep space glow", "Cosmic",
                 "space galaxy planet star alien orbit astronaut cosmic nebula starship spaceship wormhole mars moon "
                 "universe interstellar extraterrestrial ufo spacecraft gravity black_hole asteroid comet satellite "
                 "cosmos lunar solar saturn"),
    "tech": _a("#13a36b", "#0d3b2e", "#b8c4cc", "sparks", "space_hum", 0.016, 0.3, "metallic futurism", "Tech",
               "avenger superhero multiverse doom armor armour suit shield quantum android robot mech machine "
               "ai artificial_intelligence cyborg nanotech laboratory scientist experiment superpower villain "
               "metallic iron spider web"),
    "neon": _a("#ff2fb4", "#2b0b52", "#00f0ff", "rain", "city_night", 0.022, 0.45, "neon noir", "Neon",
               "neon cyber cyberpunk hacker hacking chrome synth virtual glitch matrix rave nightclub club dj "
               "megacity hologram simulation digital"),
    "horror": _a("#b3122e", "#1a0508", "#e8d9b0", "mist", "heartbeat", 0.034, 0.5, "dread red", "Horror",
                 "haunted haunting ghost curse cursed demon demonic blood bloody possessed possession witch lantern "
                 "hollow evil nightmare zombie exorcism exorcist paranormal spirit supernatural creepy terror "
                 "sinister occult vampire slasher scream fear seance asylum knocking"),
    "inferno": _a("#ff5a1f", "#4a1206", "#ffc15e", "embers", "ember_crackle", 0.02, 0.4, "ember glow", "Inferno",
                  "fire dragon ash flame volcano lava rage agni inferno burn burning blaze explosion explosive atomic "
                  "bomb firefighter phoenix hell fiery forged"),
    "frost": _a("#8fd3ff", "#1d3b56", "#ffffff", "snow", "desert_wind", 0.024, 0.15, "glacial calm", "Frost",
                "snow ice icy frozen frost winter arctic antarctic glacier cold blizzard polar himalaya himalayan "
                "avalanche everest yeti snowfall"),
    "jungle": _a("#3fae4a", "#16361b", "#e3d26f", "leaves", "forest", 0.022, 0.2, "lush canopy", "Jungle",
                 "jungle forest tribe tribal wild wilderness tiger elephant river village safari rainforest "
                 "nature animal ranger poacher bamboo amazon wildlife dinosaur hill"),
    "noir": _a("#3aa7a3", "#0e1f26", "#d9c08b", "rain", "rain", 0.026, 0.2, "cold noir", "Noir",
               "detective murder heist secret conspiracy spy agent investigation investigator cop police inspector "
               "clue mystery corruption crime criminal whodunit noir thief robbery"),
    "underworld": _a("#d4572a", "#1c1410", "#e6b450", "mist", "city_night", 0.03, 0.25, "gritty gold & smoke",
                     "Underworld",
                     "gang gangster mafia smuggling smuggler smuggle kingpin cartel don mob mobster underworld "
                     "syndicate gold mine mining coal sandalwood red_sandalwood drug empire rival boss ruthless "
                     "crime_lord slum"),
    "kinetic": _a("#f26b1d", "#0f2733", "#4fc3f7", "sparks", "city_night", 0.018, 0.35, "kinetic orange & teal",
                  "Kinetic",
                  "action chase explosion mission assassin hitman car speed race racing street fight fighting "
                  "bullet gun shootout vengeance revenge vengeful kill killing hunt hunter rescue stunt martial "
                  "kung_fu karate commando mercenary bodyguard target defeat"),
    "suspense": _a("#5b7fa6", "#0d1520", "#ff4d4d", "mist", "rain", 0.028, 0.3, "cold steel suspense", "Suspense",
                   "thriller suspense obsession psychological stalker serial_killer hostage kidnapping kidnapped "
                   "abduction amnesia paranoia twist trap escape missing vanish disappearance lie deception "
                   "fugitive insane chaos"),
    "romance": _a("#ff6f91", "#4b1730", "#ffd1a6", "petals", "rain", 0.014, 0.2, "rose dusk", "Romance",
                  "love lover heart wedding letter monsoon kiss bride groom valentine together romance romantic "
                  "marriage married engagement couple soulmate crush relationship sweetheart"),
    "pop": _a("#ff4fa3", "#3a0f3d", "#7ee8fa", "petals", "music_box", 0.008, 0.4, "candy pop", "Pop",
              "colorful colourful pink doll fashion glitter sparkle plastic perfect party glamour candy "
              "makeover diva cheerleader"),
    "whimsy": _a("#ffb703", "#3a86ff", "#ff5ea8", "sparks", "music_box", 0.008, 0.35, "playful pop", "Whimsy",
                 "magic magical toy pixel paws friends cartoon dream fun pet kid child children puppy kitten cat dog "
                 "animated emotion imaginary imagination wonder wonderland fairy fairy_tale talking game"),
    "sunny": _a("#ffcf3f", "#1f3a5f", "#5ee6c5", "dust", "music_box", 0.008, 0.25, "sunny comedy", "Sunny",
                "comedy funny hilarious prank road_trip vacation holiday summer beach wacky misadventure bachelor "
                "roommate neighbour neighbor comedian"),
    "stage": _a("#f5b942", "#26103d", "#ff5c8a", "dust", "lounge", 0.02, 0.3, "spotlight & velvet", "Stage",
                "music musician jazz singer song band concert stage piano pianist guitar guitarist rock rockstar "
                "melody rhythm dance dancer dancing hip_hop rapper rap opera orchestra musical broadway audition "
                "composer album actress actor hollywood"),
    "royal": _a("#8e44ad", "#2a0f3b", "#f1c40f", "dust", "cavern", 0.018, 0.25, "regal twilight", "Royal",
                "kingdom king queen throne sword legend prince princess crown castle knight emperor realm sorcerer "
                "wizard quest warrior palace fort conquest"),
    "mythic": _a("#ff8c1a", "#3b1405", "#ffd36b", "embers", "temple_bells", 0.02, 0.3, "saffron & temple gold",
                 "Mythic",
                 "god goddess deity divine avatar temple vishnu shiva krishna rama hanuman lord demon prophecy "
                 "ritual tradition ancestor ancestral folklore myth mythology mythological dharma karma mahabharata "
                 "ramayana kurukshetra asura devotion devotee sacred holy reincarnation reborn kalki kasi varanasi "
                 "guardian deities"),
    "battlefield": _a("#8a9a5b", "#1e2316", "#ff9b45", "dust", "ember_crackle", 0.03, 0.3, "smoke & olive drab",
                      "Battlefield",
                      "war soldier army battlefield battle trench troop regiment world_war wwii frontline sniper "
                      "platoon military general colonel siege invasion resistance rebel revolution revolutionary "
                      "freedom_fighter border"),
    "period": _a("#c49a6c", "#3b2a1d", "#efe1c6", "dust", "none", 0.015, 0.1, "sepia warmth", "Period",
                 "century freedom independence biopic true_story colonial vintage british raj history historical "
                 "era victorian memoir legacy biography physicist"),
    "intimate": _a("#e0a458", "#2b1a2e", "#f6d7b0", "dust", "none", 0.014, 0.12, "candlelit drama", "Intimate",
                   "grief loss memory mother father daughter son sister brother widow widower reunion confession "
                   "healing postman home hometown"),
    "arena": _a("#2f80ed", "#10233f", "#f2c94c", "dust", "stadium", 0.01, 0.3, "floodlight energy", "Arena",
                "cricket football soccer match stadium team champion championship boxing boxer tournament "
                "coach wrestling wrestler kabaddi hockey athlete olympic medal league player"),
}

# genre -> {archetype: weight}. Covers every TMDB genre plus the labels Indian
# listings use. Unknown compound genres ("Action Thriller") get split and retried.
GENRES: dict[str, dict[str, float]] = {
    "action": {"kinetic": 2.5},
    "adventure": {"jungle": 0.8, "desert": 0.7, "sky": 0.5, "ocean": 0.5, "kinetic": 0.4},
    "animation": {"whimsy": 2.5},
    "anime": {"whimsy": 1.2, "neon": 1.2},
    "biography": {"period": 2.0, "intimate": 0.8},
    "comedy": {"sunny": 2.0, "whimsy": 0.6},
    "crime": {"noir": 1.8, "underworld": 1.4},
    "cyberpunk": {"neon": 3.0},
    "devotional": {"mythic": 3.0},
    "disaster": {"inferno": 1.5, "ocean": 0.8},
    "documentary": {"period": 1.2, "intimate": 1.0},
    "drama": {"intimate": 1.6},
    "dystopian": {"wasteland": 2.5},
    "epic": {"royal": 1.5, "mythic": 0.8},
    "family": {"whimsy": 2.0, "sunny": 0.6},
    "fantasy": {"royal": 2.0, "mythic": 0.8},
    "gangster": {"underworld": 3.0},
    "heist": {"noir": 1.5, "kinetic": 1.0},
    "history": {"period": 2.5},
    "horror": {"horror": 3.0},
    "kids": {"whimsy": 2.5},
    "martial arts": {"kinetic": 2.0},
    "masala": {"kinetic": 1.5, "sunny": 0.8},
    "music": {"stage": 3.0},
    "musical": {"stage": 3.0},
    "mystery": {"noir": 2.0, "suspense": 0.6},
    "mythology": {"mythic": 3.0},
    "mythological": {"mythic": 3.0},
    "period": {"period": 2.5},
    "political": {"period": 1.0, "suspense": 1.0},
    "post-apocalyptic": {"wasteland": 3.0},
    "psychological": {"suspense": 2.0},
    "romance": {"romance": 2.5},
    "romantic": {"romance": 2.5},
    "rom-com": {"romance": 2.0, "sunny": 1.2},
    "science fiction": {"cosmic": 2.0, "tech": 1.0},
    "sport": {"arena": 3.0},
    "sports": {"arena": 3.0},
    "spy": {"noir": 1.5, "kinetic": 1.0},
    "superhero": {"tech": 2.5},
    "supernatural": {"horror": 1.5, "mythic": 0.6},
    "survival": {"wasteland": 1.0, "frost": 0.5, "jungle": 0.5},
    "teen": {"sunny": 1.0, "pop": 0.8},
    "thriller": {"suspense": 2.0},
    "tv movie": {},
    "war": {"battlefield": 3.0},
    "western": {"desert": 2.5},
}

GENRE_ALIASES = {
    "sci-fi": "science fiction", "scifi": "science fiction", "sci fi": "science fiction",
    "science-fiction": "science fiction", "romcom": "rom-com", "romantic comedy": "rom-com",
    "post apocalyptic": "post-apocalyptic", "martial-arts": "martial arts", "biopic": "biography",
}

# colour words in a synopsis are evidence too ("red sandalwood", "pink world")
COLOUR_WORDS = {
    "red": "#d7263d", "crimson": "#b3122e", "scarlet": "#d62828", "pink": "#ff4fa3", "rose": "#ff6f91",
    "orange": "#ff7a1a", "saffron": "#ff9933", "amber": "#ffb000", "gold": "#e6b450", "golden": "#e6b450",
    "yellow": "#ffd23f", "green": "#2fbf71", "emerald": "#1db36b", "jade": "#2fa67a", "teal": "#1fa3a3",
    "cyan": "#22d3ee", "turquoise": "#2ad4c4", "blue": "#2f6fed", "azure": "#3b9cff", "violet": "#7c4dff",
    "purple": "#8e44ad", "lavender": "#b39ddb", "magenta": "#ff2fb4", "indigo": "#4b3fcf",
}
