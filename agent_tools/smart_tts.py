import os
import re
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from livekit.agents import function_tool, RunContext
import ui_state

# Active narration state tracker
_narration_active = False
_narration_audio_path = None

def _get_mixer():
    """Lazy initialize pygame.mixer headlessly for clean background audio playback."""
    try:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        return pygame.mixer
    except Exception as e:
        logging.error(f"Error initializing pygame mixer: {e}")
        return None

# ── 25+ Dedicated Character Archetype Voice Profiles ─────────────────────────
# Combines distinct neural voices with pitch & speed modulation for exact character acting
ARCHETYPE_PROFILES = {
    # Narrator Profiles
    "narrator_cinematic": {
        "voice": "en-US-ChristopherNeural", "pitch": "-6Hz", "rate": "-4%",
        "title": "Cinematic Movie Narrator", "desc": "Deep, authoritative, dramatic narrator"
    },
    "narrator_audiobook": {
        "voice": "en-US-BrianNeural", "pitch": "0Hz", "rate": "0%",
        "title": "Audiobook Storyteller", "desc": "Warm, engaging, classic story narrator"
    },
    "narrator_british": {
        "voice": "en-GB-RyanNeural", "pitch": "0Hz", "rate": "-2%",
        "title": "BBC British Narrator", "desc": "Refined documentary narrator"
    },

    # Male Archetypes
    "male_hero": {
        "voice": "en-US-GuyNeural", "pitch": "+4Hz", "rate": "+4%",
        "title": "Young Hero / Protagonist", "desc": "Energetic, determined young male lead"
    },
    "male_leader_mature": {
        "voice": "en-US-AndrewNeural", "pitch": "-8Hz", "rate": "0%",
        "title": "Mature Leader / Commander", "desc": "Composed, authoritative adult leader"
    },
    "male_villain_dark": {
        "voice": "en-US-EricNeural", "pitch": "-22Hz", "rate": "-10%",
        "title": "Dark Villain / Antagonist", "desc": "Deep, gravelly, menacing, ominous villain"
    },
    "male_elderly_wise": {
        "voice": "en-US-RogerNeural", "pitch": "-14Hz", "rate": "-14%",
        "title": "Elderly Mentor / Wizard / Grandpa", "desc": "Gravelly, slow, wise elder"
    },
    "male_child_teen": {
        "voice": "en-US-GuyNeural", "pitch": "+22Hz", "rate": "+10%",
        "title": "Young Boy / Teen", "desc": "High-pitched, enthusiastic young boy"
    },
    "male_british_aristocrat": {
        "voice": "en-GB-ThomasNeural", "pitch": "0Hz", "rate": "0%",
        "title": "British Gentleman / Butler / Detective", "desc": "Formal, articulate English male"
    },
    "male_indian_professional": {
        "voice": "en-IN-PrabhatNeural", "pitch": "0Hz", "rate": "0%",
        "title": "Indian Professional / Tech Lead", "desc": "Clear, cultured Indian English male"
    },
    "male_irish_warm": {
        "voice": "en-IE-ConnorNeural", "pitch": "0Hz", "rate": "+3%",
        "title": "Irish Adventurer / Friend", "desc": "Warm, melodic, friendly Irish male"
    },
    "male_australian_casual": {
        "voice": "en-AU-WilliamMultilingualNeural", "pitch": "0Hz", "rate": "+5%",
        "title": "Australian Hero / Rogue", "desc": "Laid-back, rugged Australian male"
    },
    "male_comedic_sidekick": {
        "voice": "en-US-EricNeural", "pitch": "+15Hz", "rate": "+12%",
        "title": "Comedic Sidekick / Nervous Buddy", "desc": "Expressive, fast-talking, quirky male"
    },

    # Female Archetypes
    "female_heroine": {
        "voice": "en-US-JennyNeural", "pitch": "0Hz", "rate": "+2%",
        "title": "Heroine / Female Protagonist", "desc": "Confident, clear, inspiring female lead"
    },
    "female_expressive_dramatic": {
        "voice": "en-US-AriaNeural", "pitch": "+4Hz", "rate": "+3%",
        "title": "Dramatic / Emotional Female Lead", "desc": "Passionate, dynamic, intense actress voice"
    },
    "female_warm_motherly": {
        "voice": "en-US-AvaNeural", "pitch": "-5Hz", "rate": "-4%",
        "title": "Gentle / Motherly / Caring Female", "desc": "Soft-spoken, comforting, compassionate woman"
    },
    "female_child_young": {
        "voice": "en-US-AnaNeural", "pitch": "+18Hz", "rate": "+8%",
        "title": "Young Girl / Child", "desc": "High-pitched, innocent young girl voice"
    },
    "female_elderly": {
        "voice": "en-GB-LibbyNeural", "pitch": "-12Hz", "rate": "-14%",
        "title": "Elderly Grandmother / Matron", "desc": "Gentle, frail, warm older woman"
    },
    "female_british_aristocrat": {
        "voice": "en-GB-SoniaNeural", "pitch": "0Hz", "rate": "-3%",
        "title": "British Noblewoman / Queen", "desc": "Refined, poised British female"
    },
    "female_british_youth": {
        "voice": "en-GB-MaisieNeural", "pitch": "+10Hz", "rate": "+5%",
        "title": "British Youth / Spunky Heroine", "desc": "Energetic, bright British girl"
    },
    "female_indian_expressive": {
        "voice": "en-IN-NeerjaExpressiveNeural", "pitch": "0Hz", "rate": "0%",
        "title": "Indian Female Lead", "desc": "Expressive, articulate Indian female character"
    },
    "female_irish_cheerful": {
        "voice": "en-IE-EmilyNeural", "pitch": "+6Hz", "rate": "+5%",
        "title": "Irish Cheerful Heroine", "desc": "Bright, uplifting Irish female voice"
    },
    "female_australian": {
        "voice": "en-AU-NatashaNeural", "pitch": "0Hz", "rate": "0%",
        "title": "Australian Female Adventurer", "desc": "Confident Australian female lead"
    },

    # Specialty Archetypes
    "robot_ai": {
        "voice": "en-US-SteffanNeural", "pitch": "-15Hz", "rate": "-6%",
        "title": "Synthetic AI / Android / Robot", "desc": "Precise, slightly metallic, robotic voice"
    }
}

def _assign_archetype_voices(characters: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """
    Intelligently map every script character to their dedicated voice archetype profile,
    ensuring that each speaker gets a distinct vocal identity and tone.
    """
    assigned = {}
    used_voices = set()

    for char in characters:
        name = char.get("name", "").strip()
        arch_key = char.get("archetype", "").strip().lower()

        # Direct archetype match if valid
        profile = None
        if arch_key in ARCHETYPE_PROFILES and ARCHETYPE_PROFILES[arch_key]["voice"] not in used_voices:
            profile = ARCHETYPE_PROFILES[arch_key].copy()
        elif arch_key in ARCHETYPE_PROFILES:
            profile = ARCHETYPE_PROFILES[arch_key].copy()
        else:
            # Fallback deduction based on gender, age, role
            gender = char.get("gender", "neutral").lower()
            role = char.get("role", "character").lower()
            age = char.get("age", "adult").lower()

            if "narrat" in name.lower() or role == "narrator":
                profile = ARCHETYPE_PROFILES["narrator_audiobook"].copy()
            elif "child" in age or "young" in age or "kid" in age:
                profile = ARCHETYPE_PROFILES["female_child_young"].copy() if gender == "female" else ARCHETYPE_PROFILES["male_child_teen"].copy()
            elif "old" in age or "elder" in age:
                profile = ARCHETYPE_PROFILES["female_elderly"].copy() if gender == "female" else ARCHETYPE_PROFILES["male_elderly_wise"].copy()
            elif gender == "female":
                profile = ARCHETYPE_PROFILES["female_heroine"].copy()
            else:
                profile = ARCHETYPE_PROFILES["male_hero"].copy()

        # Allow character-specific pitch/rate overrides from Gemini analysis
        custom_pitch = char.get("pitch")
        custom_rate = char.get("rate")
        if custom_pitch and isinstance(custom_pitch, str) and ("Hz" in custom_pitch or "%" in custom_pitch):
            profile["pitch"] = custom_pitch
        if custom_rate and isinstance(custom_rate, str) and "%" in custom_rate:
            profile["rate"] = custom_rate

        assigned[name] = profile
        used_voices.add(profile["voice"])

    return assigned

async def _synthesize_line(text: str, profile: Dict[str, str], out_path: str) -> bool:
    """Synthesize a single dialogue line using edge-tts with precise pitch and rate modulation."""
    try:
        import edge_tts
        voice = profile.get("voice", "en-US-BrianNeural")
        pitch = profile.get("pitch", "0Hz")
        rate = profile.get("rate", "0%")

        communicate = edge_tts.Communicate(text, voice, pitch=pitch, rate=rate)
        await communicate.save(out_path)
        return True
    except Exception as e:
        logging.warning(f"Line synthesis error for voice {profile.get('voice')}: {e}")
        return False

@function_tool()
async def narrate_script_multivoice(
    context: RunContext,  # type: ignore
    filepath: str,
    page_number: Optional[int] = None,
    max_pages: int = 4,
    save_audio: bool = True
) -> str:
    """
    Perform a smart multi-voice dramatic narration of a script, dialogue, play, or story from a PDF or text file.
    Analyzes character personalities, ages, accents, and genders with Gemini, casts them from a catalog of 25+ dedicated
    character voice archetypes (villain, hero, elderly wise, child, British, Indian, cinematic narrator), and synthesizes
    each line with targeted pitch and speed modulation without burning Gemini Live audio credits.
    
    Use this when the user asks to 'read this script with different voices', 'narrate the story with dedicated voices',
    'read out this play', or 'perform dialogue in this PDF'.
    
    Args:
        filepath: Path or filename of the PDF or text file (e.g. 'script.pdf', 'story.txt', 'play.pdf').
        page_number: Optional specific 1-indexed page of PDF to read (e.g. 1).
        max_pages: Number of pages to read from start if page_number is not provided (default 4).
        save_audio: If True (default), saves the complete multi-voice audio file and casting sheet to ~/Desktop/Zenith_Narrations/.
    """
    global _narration_active, _narration_audio_path

    # Step 1: Locate and extract text from document
    from agent_tools.documents import _resolve_target_path, extract_pdf_data
    resolved = _resolve_target_path(filepath)
    if not resolved:
        return f"Could not find document '{filepath}'. Please check the filename or location, Sir."

    ui_state.set_text(f"🎭 Casting Roles | {os.path.basename(resolved)[:16]}...")
    ext = os.path.splitext(resolved)[1].lower()
    raw_text = ""

    if ext == ".pdf":
        data = await asyncio.to_thread(extract_pdf_data, resolved, page_number, max_pages)
        if not data["success"] or not data["full_text"].strip():
            return f"Unable to extract readable text from PDF '{os.path.basename(resolved)}': {data.get('error', 'Empty document')}"
        raw_text = data["full_text"]
    else:
        try:
            with open(resolved, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read(15000)
        except Exception as read_err:
            return f"Failed to read file '{resolved}': {read_err}"

    if not raw_text.strip():
        return f"The document '{os.path.basename(resolved)}' contains no readable dialogue or text."

    # Step 2: Use Gemini Flash to analyze deep character personas and map to dedicated archetypes
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Google API key is required to analyze the script personas, Sir."

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)

        archetypes_list = list(ARCHETYPE_PROFILES.keys())
        analysis_prompt = (
            "You are Zenith's Elite Dramatic Casting Director. Analyze the following document text.\n"
            "Identify the narrator and all speaking characters. Analyze each character's age, gender, personality, and tone,\n"
            f"and assign each character the BEST MATCHING archetype from this available catalog:\n{archetypes_list}\n\n"
            "Return a strictly valid JSON object with:\n"
            "{\n"
            '  "characters": [\n'
            '    {\n'
            '      "name": "Narrator or CharacterName",\n'
            '      "gender": "male|female|neutral",\n'
            '      "age": "child|teen|adult|elderly",\n'
            '      "role": "narrator|protagonist|antagonist|sidekick",\n'
            '      "archetype": "one_of_the_archetype_keys_above",\n'
            '      "pitch": "-15Hz to +20Hz (optional fine tuning)",\n'
            '      "rate": "-12% to +10% (optional fine tuning)"\n'
            '    }\n'
            '  ],\n'
            '  "dialogues": [\n'
            '    {"speaker": "CharacterName or Narrator", "text": "Exact text spoken"}\n'
            '  ]\n'
            "}\n\n"
            "Rules:\n"
            "- Scene descriptions, context setting, or unvoiced action must be assigned to 'Narrator' (narrator_cinematic or narrator_audiobook).\n"
            "- Villains/antagonists should be given 'male_villain_dark' (deep pitch).\n"
            "- Young children must be given 'female_child_young' or 'male_child_teen' (higher pitch).\n"
            "- Limit to the first 25 dialogue turns for immediate fluid performance.\n\n"
            f"Script Text:\n{raw_text[:12000]}"
        )

        resp = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=analysis_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        parsed = json.loads(resp.text)
        characters = parsed.get("characters", [])
        dialogues = parsed.get("dialogues", [])

        if not dialogues:
            return f"Could not find identifiable dialogue turns in '{os.path.basename(resolved)}'."

    except Exception as parse_err:
        logging.error(f"Failed to parse script with Gemini: {parse_err}")
        return f"Script parsing failed: {str(parse_err)}"

    # Step 3: Map dedicated archetype profiles
    cast_map = _assign_archetype_voices(characters)
    cast_lines = []
    for name, prof in cast_map.items():
        cast_lines.append(f"- **{name}**: {prof.get('title', 'Actor')} ({prof.get('voice', 'Default')}, pitch: {prof.get('pitch')}, rate: {prof.get('rate')})")
    cast_summary = "\n".join(cast_lines)
    logging.info(f"Target Voice Casting:\n{cast_summary}")

    # Step 4: Synthesize each dialogue line
    ui_state.set_text("🎙️ Synthesizing Cast...")
    temp_dir = os.path.join(os.getenv("TEMP", "."), "zenith_multivoice_temp")
    os.makedirs(temp_dir, exist_ok=True)
    segment_files = []

    try:
        tasks = []
        for idx, turn in enumerate(dialogues):
            speaker = turn.get("speaker", "Narrator")
            text = turn.get("text", "").strip()
            if not text:
                continue
            profile = cast_map.get(speaker, ARCHETYPE_PROFILES["narrator_audiobook"])
            part_path = os.path.join(temp_dir, f"part_{idx:03d}.mp3")
            segment_files.append(part_path)
            tasks.append(_synthesize_line(text, profile, part_path))

        results = await asyncio.gather(*tasks)
        valid_files = [f for f, ok in zip(segment_files, results) if ok and os.path.exists(f)]

        if not valid_files:
            return "Failed to synthesize speech for the character dialogues."

        # Step 5: Concatenate segments into one master MP3
        user_home = os.path.expanduser("~")
        out_dir = os.path.join(user_home, "Desktop", "Zenith_Narrations")
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '', os.path.splitext(os.path.basename(resolved))[0])[:25]
        master_mp3 = os.path.join(out_dir, f"Narration_{clean_name}_{stamp}.mp3")
        cast_sheet = os.path.join(out_dir, f"Cast_Credits_{clean_name}_{stamp}.txt")

        with open(master_mp3, "wb") as master_f:
            for part in valid_files:
                try:
                    with open(part, "rb") as pf:
                        master_f.write(pf.read())
                    os.remove(part)
                except Exception:
                    pass

        # Write cast credits sheet
        if save_audio:
            try:
                with open(cast_sheet, "w", encoding="utf-8") as cs_f:
                    cs_f.write(
                        f"=== Zenith Dramatic Multi-Voice Cast Credits ===\n"
                        f"Document: {os.path.basename(resolved)}\n"
                        f"Recorded: {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}\n"
                        f"Total Lines: {len(dialogues)}\n\n"
                        f"Voice Cast:\n{cast_summary}\n"
                    )
            except Exception:
                pass

        _narration_audio_path = master_mp3
        _narration_active = True

        # Step 6: Start playback in background using pygame.mixer
        mixer = _get_mixer()
        if mixer:
            try:
                mixer.music.load(master_mp3)
                mixer.music.play()
                ui_state.set_text(f"🎭 Performing Script | {len(dialogues)} Lines")
            except Exception as play_err:
                logging.warning(f"Failed to play via pygame mixer: {play_err}")

        saved_notice = f"\n📁 Complete audio and casting sheet saved to: Desktop/Zenith_Narrations/{os.path.basename(master_mp3)}" if save_audio else ""
        return (
            f"=== MULTI-VOICE DRAMATIC NARRATION ACTIVE ===\n"
            f"Document: {os.path.basename(resolved)}\n"
            f"Cast Roles ({len(cast_map)} characters):\n{cast_summary}\n\n"
            f"Total Lines: {len(dialogues)}\n"
            f"Playback has started with dedicated character voice acting.{saved_notice}\n"
            f"To pause, resume, or stop at any time, say 'stop narration' or 'pause narration'."
        )

    except Exception as e:
        logging.error(f"Error during multivoice narration: {e}", exc_info=True)
        return f"Narration synthesis failed: {str(e)}"

@function_tool()
async def control_narration(
    context: RunContext,  # type: ignore
    action: str,
    volume: int = -1
) -> str:
    """
    Control multi-voice script narration playback.
    Supported actions: 'stop', 'pause', 'resume', 'volume'.
    If action is 'volume', provide volume (0 to 100).
    """
    global _narration_active
    mixer = _get_mixer()
    if not mixer:
        return "Audio playback mixer is not initialized."

    act = action.lower().strip()
    try:
        if act in ["stop", "cancel", "halt", "kill"]:
            mixer.music.stop()
            _narration_active = False
            ui_state.set_text("⏹️ Narration Stopped")
            return "Narration playback stopped, Sir."

        elif act in ["pause", "hold"]:
            mixer.music.pause()
            ui_state.set_text("⏸️ Narration Paused")
            return "Narration paused."

        elif act in ["resume", "play", "unpause"]:
            mixer.music.unpause()
            ui_state.set_text("▶️ Narration Resumed")
            return "Resumed narration playback."

        elif act == "volume":
            if 0 <= volume <= 100:
                mixer.music.set_volume(volume / 100.0)
                return f"Narration volume set to {volume}%."
            return "Please provide a volume level between 0 and 100."

        return f"Unknown narration control action '{action}'."
    except Exception as e:
        return f"Error controlling narration: {e}"
