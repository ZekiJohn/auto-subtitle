import os
import ffmpeg
import whisper
import argparse
import warnings
import tempfile
import pysubs2
from .utils import filename, str2bool, write_srt, write_ass


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("video", nargs="+", type=str,
                        help="paths to video files to transcribe")
    parser.add_argument("--model", default="small",
                        choices=whisper.available_models(), help="name of the Whisper model to use")
    parser.add_argument("--output_dir", "-o", type=str,
                        default=".", help="directory to save the outputs")
    parser.add_argument("--output_srt", type=str2bool, default=False,
                        help="whether to output the .srt file along with the video files")
    parser.add_argument("--srt_only", type=str2bool, default=False,
                        help="only generate the .srt file and not create overlayed video")
    parser.add_argument("--verbose", type=str2bool, default=False,
                        help="whether to print out the progress and debug messages")

    parser.add_argument("--task", type=str, default="transcribe", choices=[
                        "transcribe", "translate"], help="whether to perform X->X speech recognition ('transcribe') or X->English translation ('translate')")
    parser.add_argument("--language", type=str, default="auto", choices=["auto","af","am","ar","as","az","ba","be","bg","bn","bo","br","bs","ca","cs","cy","da","de","el","en","es","et","eu","fa","fi","fo","fr","gl","gu","ha","haw","he","hi","hr","ht","hu","hy","id","is","it","ja","jw","ka","kk","km","kn","ko","la","lb","ln","lo","lt","lv","mg","mi","mk","ml","mn","mr","ms","mt","my","ne","nl","nn","no","oc","pa","pl","ps","pt","ro","ru","sa","sd","si","sk","sl","sn","so","sq","sr","su","sv","sw","ta","te","tg","th","tk","tl","tr","tt","uk","ur","uz","vi","yi","yo","zh"], 
    help="What is the origin language of the video? If unset, it is detected automatically.")

    args = parser.parse_args().__dict__
    model_name: str = args.pop("model")
    output_dir: str = args.pop("output_dir")
    output_srt: bool = args.pop("output_srt")
    srt_only: bool = args.pop("srt_only")
    language: str = args.pop("language")
    
    os.makedirs(output_dir, exist_ok=True)

    if model_name.endswith(".en"):
        warnings.warn(
            f"{model_name} is an English-only model, forcing English detection.")
        args["language"] = "en"
    # if translate task used and language argument is set, then use it
    elif language != "auto":
        args["language"] = language
        
    model = whisper.load_model(model_name)
    audios = get_audio(args.pop("video"))
    subtitles = get_subtitles(
        audios, output_srt or srt_only, output_dir, lambda audio_path: model.transcribe(audio_path, **args)
    )

    if srt_only:
        return

    for path, srt_path in subtitles.items():
        out_path = os.path.join(output_dir, f"{filename(path)}.mp4")

        print(f"Adding subtitles to {filename(path)}...")

        video = ffmpeg.input(path)
        audio = video.audio

        ffmpeg.concat(
            video.filter('subtitles', srt_path, force_style="OutlineColour=&H40000000,BorderStyle=3"), audio, v=1, a=1
        ).output(out_path).run(quiet=True, overwrite_output=True)

        print(f"Saved subtitled video to {os.path.abspath(out_path)}.")


def get_audio(paths):
    temp_dir = tempfile.gettempdir()

    audio_paths = {}

    for path in paths:
        print(f"Extracting audio from {filename(path)}...")
        output_path = os.path.join(temp_dir, f"{filename(path)}.wav")

        ffmpeg.input(path).output(
            output_path,
            acodec="pcm_s16le", ac=1, ar="16k"
        ).run(quiet=True, overwrite_output=True)

        audio_paths[path] = output_path

    return audio_paths


# def get_subtitles(audio_paths: list, output_ass: bool, output_dir: str, transcribe: callable):
#     subtitles_path = {}
#
#     for path, audio_path in audio_paths.items():
#         ass_path = output_dir if output_ass else tempfile.gettempdir()
#         ass_path = os.path.join(ass_path, f"{filename(path)}.ass")
#
#         print(f"Generating ASS subtitles for {filename(path)}... This might take a while.")
#
#         warnings.filterwarnings("ignore")
#         result = transcribe(audio_path)
#         warnings.filterwarnings("default")
#
#         # Now we create an ASS file instead of SRT
#         subs = pysubs2.SSAFile()
#         style = pysubs2.SSAStyle()
#         style.fontname = "Arial"
#         style.fontsize = 20
#         style.primarycolor = pysubs2.Color(255, 255, 255, 0)  # White, fully opaque
#         style.secondarycolor = pysubs2.Color(255, 255, 255, 0)  # White, fully opaque
#         style.outlinecolor = pysubs2.Color(0, 0, 0, 0)  # Black, fully opaque
#         style.backcolor = pysubs2.Color(255, 0, 0, 128)  # Red, 50% transparent
#         style.alignment = 2  # Centered at the bottom
#
#         # Add the style to the SSAFile
#         subs.styles["Default"] = style
#         # subs.styles["Default"] = pysubs2.SSAStyle(primarycolor="#FFFFFF", secondarycolor="#FFFF00", outlinecolor="#000000")
#         # Add more styles if needed
#
#         # Convert the transcription segments into ASS dialogue lines
#         for segment in result["segments"]:
#             start_time = int(segment["start"] * 1000)  # Assuming these are in seconds
#             end_time = int(segment["end"] * 1000)
#             text = segment["text"]
#
#             # Create a new event for each line of subtitles
#             line = pysubs2.SSAEvent(start=start_time, end=end_time, text=text)
#             line.style = "Default"  # Set the style to "Default" or any other predefined style
#
#             # Append the event to the subs object
#             subs.events.append(line)
#
#         # Save the subtitles to an .ass file
#         subs.save(ass_path)
#
#         subtitles_path[path] = ass_path
#
#     return subtitles_path

def get_subtitles(audio_paths: list, output_srt: bool, output_dir: str, transcribe: callable):
    subtitles_path = {}

    for path, audio_path in audio_paths.items():
        srt_path = output_dir if output_srt else tempfile.gettempdir()
        srt_path = os.path.join(srt_path, f"{filename(path)}.srt")

        print(
            f"Generating subtitles for {filename(path)}... This might take a while."
        )

        warnings.filterwarnings("ignore")
        result = transcribe(audio_path)
        warnings.filterwarnings("default")

        with open(srt_path, "w", encoding="utf-8") as srt:
            # write_srt(result["segments"], file=srt)
            write_ass(result["segments"], file=srt)

        subtitles_path[path] = srt_path

    return subtitles_path


if __name__ == '__main__':
    main()
