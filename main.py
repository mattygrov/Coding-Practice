from flask import Flask, request, jsonify
import subprocess
import os
import re

app = Flask(__name__)

@app.route("/")
def home():
    return "YouTube Transcript API is running!"

@app.route("/transcript", methods=["GET"])
def get_transcript():
    video_id = request.args.get("video_id")
    if not video_id:
        return jsonify({"error": "Missing video_id"}), 400

    try:
        # Run yt-dlp to fetch auto-generated subtitles
        command = [
    "yt-dlp",
    "--write-auto-sub",
    "--sub-lang", "en",
    "--skip-download",
    f"https://www.youtube.com/watch?v={video_id}",
    "--cookies", "cookies.txt"
    "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
]
        subprocess.run(command, check=True)

        # Look for the downloaded VTT file
        vtt_file = next((f for f in os.listdir() if f.endswith(".en.vtt")), None)
        if not vtt_file:
            return jsonify({"error": "Transcript not found"}), 404

        # Process the VTT file: remove timestamps and any HTML-like tags (e.g. <c>)
        transcript_lines = []
        with open(vtt_file, "r", encoding="utf-8") as f:
            for line in f:
                # Skip lines that contain timecodes
                if "-->" in line:
                    continue
                # Remove any tags such as <c>...</c> using regex
                cleaned_line = re.sub(r'<[^>]+>', '', line)
                cleaned_line = cleaned_line.strip()

                if cleaned_line:
                    transcript_lines.append(cleaned_line)

        # Optional: remove duplicate lines if needed
        unique_lines = []
        seen = set()
        for line in transcript_lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)

        final_transcript = " ".join(unique_lines)

        # Clean up: remove the temporary VTT file
        os.remove(vtt_file)

        # Return JSON with "captions" so Tana can map it into the Captions field
        return jsonify({
            "video_id": video_id,
            "captions": final_transcript
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

import os

port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
