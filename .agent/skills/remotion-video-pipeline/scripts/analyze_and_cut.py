import argparse
import subprocess
import json
import os
import sys

def check_dependencies():
    """Checks if ffmpeg and whisper are available."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except FileNotFoundError:
        print("Error: ffmpeg is not installed or not in PATH.")
        sys.exit(1)
    
    try:
        import whisper
    except ImportError:
        print("Error: openai-whisper python package is not installed. Run: pip install openai-whisper")
        sys.exit(1)

def transcribe_video(video_path, model_size="base"):
    """Transcribes video using Whisper."""
    import whisper
    print(f"Loading Whisper model '{model_size}'...")
    model = whisper.load_model(model_size)
    print(f"Transcribing '{video_path}'...")
    result = model.transcribe(video_path, word_timestamps=True)
    return result

def identify_clean_take(transcript):
    """
    Analyzes transcript to find the 'clean take'.
    
    Heuristic:
    - Looks for phrases like "Take 2", "Start over", etc.
    - If found, assumes the content AFTER that marker is the clean take.
    - If not found, assumes the entire video is the clean take (minus silence at ends).
    
    This is a basic implementation. Custom logic should be added here.
    """
    segments = transcript.get("segments", [])
    if not segments:
        return 0, None # Start to End

    cut_start_time = 0.0
    
    # Simple heuristic keywords
    reset_keywords = ["take two", "take 2", "start over", "scratch that", "again"]
    
    for segment in segments:
        text = segment["text"].lower()
        if any(keyword in text for keyword in reset_keywords):
            print(f"Detected reset marker: '{text.strip()}' at {segment['end']}s")
            cut_start_time = segment["end"]
            
    # Find the end (last spoken word)
    cut_end_time = segments[-1]["end"]
    
    print(f"Identified clean take: {cut_start_time}s to {cut_end_time}s")
    return cut_start_time, cut_end_time

def cut_video(input_path, output_path, start_time, end_time):
    """Cuts the video using FFMPEG."""
    duration = end_time - start_time
    cmd = [
        "ffmpeg",
        "-y", # Overwrite output
        "-ss", str(start_time),
        "-i", input_path,
        "-t", str(duration),
        "-c", "copy", # Fast stream copy
        output_path
    ]
    
    print(f"Running FFMPEG: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main():
    parser = argparse.ArgumentParser(description="Analyze and cut video based on voice command structure.")
    parser.add_argument("input_video", help="Path to input video file")
    parser.add_argument("--output", "-o", help="Path to output cut video", default="cut_output.mp4")
    parser.add_argument("--model", help="Whisper model size", default="base")
    
    args = parser.parse_args()
    
    check_dependencies()
    
    transcript = transcribe_video(args.input_video, args.model)
    start, end = identify_clean_take(transcript)
    
    if end is None:
        print("Could not determine end time. Using full duration.")
        # FFMpeg without -t will go to end if we just set start
    
    cut_video(args.input_video, args.output, start, end or 999999)
    print(f"Successfully created {args.output}")

if __name__ == "__main__":
    main()
