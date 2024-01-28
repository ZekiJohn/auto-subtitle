import os
from typing import Iterator, TextIO
import pysubs2

def str2bool(string):
    string = string.lower()
    str2val = {"true": True, "false": False}

    if string in str2val:
        return str2val[string]
    else:
        raise ValueError(
            f"Expected one of {set(str2val.keys())}, got {string}")


def format_timestamp(seconds: float, always_include_hours: bool = False):
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000

    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000

    seconds = milliseconds // 1_000
    milliseconds -= seconds * 1_000

    hours_marker = f"{hours:02d}:" if always_include_hours or hours > 0 else ""
    return f"{hours_marker}{minutes:02d}:{seconds:02d},{milliseconds:03d}"



def write_ass(transcript, file):
    # Create a new SSAFile
    subs = pysubs2.SSAFile()

    # Define the style for the subtitles
    style = pysubs2.SSAStyle()
    style.fontname = "Arial"
    style.fontsize = 20
    style.primarycolor = pysubs2.Color(255, 255, 255, 0)  # White, fully opaque
    style.secondarycolor = pysubs2.Color(255, 0, 0, 0)    # Red, fully opaque
    style.outlinecolor = pysubs2.Color(0, 0, 0, 0)        # Black, fully opaque
    style.backcolor = pysubs2.Color(0, 0, 0, 128)         # Black, 50% transparent
    style.alignment = 2  # Centered at the bottom
    subs.styles["Default"] = style

    # Convert the transcript data to subtitle events
    for segment in transcript:
        start_time = int(segment['start'] * 1000)  # Convert to milliseconds
        end_time = int(segment['end'] * 1000)
        text = segment['text'].strip().replace('-->', '->')
        event = pysubs2.SSAEvent(start=start_time, end=end_time, text=text)
        event.style = "Default"
        subs.events.append(event)

    # Save the ASS subtitle file
    subs.save(file)


def write_srt(transcript: Iterator[dict], file: TextIO):
    for i, segment in enumerate(transcript, start=1):
        print("===================================SEGMENT")
        print(segment)
        print(
            f"{i}\n"
            f"{format_timestamp(segment['start'], always_include_hours=True)} --> "
            f"{format_timestamp(segment['end'], always_include_hours=True)}\n"
            f"{segment['text'].strip().replace('-->', '->')}\n",
            file=file,
            flush=True,
        )


def filename(path):
    return os.path.splitext(os.path.basename(path))[0]
