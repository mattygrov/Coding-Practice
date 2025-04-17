from flask import Flask, request, jsonify
import subprocess
import os
import re
import json

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
        # Create a temporary cookies json file with the most important cookies
        # This is an alternative approach to using the cookies.txt file
        cookie_data = [
            {
                "name": "CONSENT", 
                "value": "YES+",
                "domain": ".youtube.com",
                "path": "/"
            },
            # Add any other cookies that might be helpful
            {
                "name": "LOGIN_INFO",
                "value": "AFmmF2swRAIgbNeSV70viWKdb6gNQu_9twFRqrGKjc-stQZCyE-HtzQCIHYgTNC1uo121SAGNUFbCxIBRnFVIR9t3xNTYAwK6o-l:QUQ3MjNmeHVTc2N2UXdrUUdMNXJpTUhzbDFka19GOFpxMmRpREtzUVpSYWFnZzE5T3REMU5DZ0RQemNSbUFvb0M4NkN3c3RNZ3ZvcnlCMVotRDlvalRQNEswSFJQOGdXTFZNYTFON2JZck45WXV6YV9pd1dBZGkwNVZtSW5LaHY1NFZtWFRuVzhMekdsbXI3dXFfRUt3S3dDa1piTENFbTBpclpPZE9TNmJrMzdhT2wzMjV5OGp4dkNST1EzYWZ3eWtBOWF1Zk8tM1ZlSWVBcFVLMklreTczUl9vVC1PR2xSUQ==",
                "domain": ".youtube.com",
                "path": "/"
            }
        ]
        
        with open('yt_cookies.json', 'w') as f:
            json.dump(cookie_data, f)
        
        # Try an alternative approach - using youtube-transcript-api
        # This could bypass the YouTube bot detection issues
        try:
            print("Attempting to use youtube-transcript-api as an alternative")
            from youtube_transcript_api import YouTubeTranscriptApi
            
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([item['text'] for item in transcript_list])
            
            return jsonify({
                "video_id": video_id,
                "captions": transcript_text
            })
        
        except Exception as transcript_api_error:
            print(f"youtube-transcript-api failed: {str(transcript_api_error)}")
            print("Falling back to yt-dlp...")
            
            # If youtube-transcript-api fails, fall back to yt-dlp with modified options
            command = [
                "yt-dlp",
                "--write-auto-sub",
                "--sub-lang", "en",
                "--skip-download",
                "--verbose",
                "--no-cache-dir",
                "--no-check-certificate",  # Skip HTTPS certificate validation
                f"https://www.youtube.com/watch?v={video_id}",
                "--cookies", "cookies.txt",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",  # Try a different user agent
                "--referer", "https://www.youtube.com/"  # Add a referer to look more like a browser
            ]
            
            # Add debug lines
            print(f"Running command: {' '.join(command)}")
            print(f"Working directory: {os.getcwd()}")
            print(f"Files in directory: {os.listdir()}")
            
            # Run the command once, with output capture
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"Command output: {result.stdout}")
            print(f"Command error: {result.stderr}")

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

    except subprocess.CalledProcessError as e:
        print(f"Command error occurred: {str(e)}")
        print(f"Command output: {e.stdout if hasattr(e, 'stdout') else 'No output'}")
        print(f"Command error output: {e.stderr if hasattr(e, 'stderr') else 'No error output'}")
        return jsonify({"error": f"Command failed: {str(e)}"}), 500
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
