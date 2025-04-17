from flask import Flask, request, jsonify
import os
import re
import requests
from html import unescape

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
        print(f"Processing transcript for video ID: {video_id}")
        
        # Try using YouTube's official timedtext API
        # This is a more reliable method that might bypass the restrictions
        print("Attempting to use YouTube's timedtext API")
        
        # First, we need to get the caption track info
        video_info_url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.youtube.com/"
        }
        
        print(f"Fetching video page: {video_info_url}")
        response = requests.get(video_info_url, headers=headers)
        html_content = response.text
        
        # Extract caption track URL from video page
        # Look for the captionTracks in the page source
        print("Extracting caption track info from page source")
        
        captions_regex = r'"captionTracks":\[(.*?)\]'
        captions_match = re.search(captions_regex, html_content)
        
        if not captions_match:
            print("No caption tracks found in video page")
            return jsonify({"error": "No captions available for this video"}), 404
        
        captions_data = captions_match.group(1)
        
        # Extract the URL for the English auto-generated captions
        url_regex = r'"baseUrl":"(.*?)"'
        url_match = re.search(url_regex, captions_data)
        
        if not url_match:
            print("Could not extract caption URL")
            return jsonify({"error": "Could not extract caption URL"}), 500
        
        # Get the caption URL and decode escape characters
        caption_url = url_match.group(1).replace('\\u0026', '&')
        print(f"Found caption URL: {caption_url}")
        
        # Add format parameters to get plain text
        caption_url = caption_url + "&fmt=json3"
        
        # Fetch the captions
        print(f"Fetching captions from: {caption_url}")
        captions_response = requests.get(caption_url, headers=headers)
        captions_data = captions_response.json()
        
        # Extract and process the transcript
        print("Processing caption data")
        transcript_parts = []
        
        # The structure of the JSON may vary, but typically it has events with text
        if 'events' in captions_data:
            for event in captions_data['events']:
                if 'segs' in event:
                    for seg in event['segs']:
                        if 'utf8' in seg:
                            text = seg['utf8']
                            # Clean up the text
                            text = text.strip()
                            if text and not text.isspace():
                                transcript_parts.append(text)
        
        if not transcript_parts:
            print("No transcript text found in caption data")
            return jsonify({"error": "No transcript text found"}), 404
        
        # Join all parts to form the complete transcript
        final_transcript = " ".join(transcript_parts)
        
        # Clean up any HTML entities
        final_transcript = unescape(final_transcript)
        
        print(f"Successfully extracted transcript with {len(transcript_parts)} segments")
        
        # Return JSON with "captions" so Tana can map it into the Captions field
        return jsonify({
            "video_id": video_id,
            "captions": final_transcript
        })

    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
