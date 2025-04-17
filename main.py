from flask import Flask, request, jsonify
import os
import requests
import html
import re

app = Flask(__name__)

# Your YouTube API key
YOUTUBE_API_KEY = "AIzaSyBQEL9ZNU7tlgsSte4362v5TsxYrsvo308"  # You'll need to replace this with your actual API key

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
        
        # Step 1: Get the caption tracks available for this video
        captions_url = f"https://www.googleapis.com/youtube/v3/captions?part=snippet&videoId={video_id}&key={YOUTUBE_API_KEY}"
        print(f"Fetching caption tracks from YouTube API")
        
        captions_response = requests.get(captions_url)
        if captions_response.status_code != 200:
            print(f"YouTube API error: {captions_response.status_code}")
            print(captions_response.text)
            return jsonify({"error": f"YouTube API error: {captions_response.text}"}), 500
        
        captions_data = captions_response.json()
        
        # Look for English captions
        caption_id = None
        for item in captions_data.get('items', []):
            language = item.get('snippet', {}).get('language', '')
            track_kind = item.get('snippet', {}).get('trackKind', '')
            
            if language == 'en' or language.startswith('en-'):
                caption_id = item.get('id')
                print(f"Found English caption track: {caption_id}, type: {track_kind}")
                break
        
        if not caption_id:
            print("No English captions found")
            
            # If no captions found through the API, try an alternative approach
            # YouTube's timedtext API (which doesn't require an API key)
            print("Trying alternative timedtext approach")
            
            timedtext_url = f"https://www.youtube.com/api/timedtext?lang=en&v={video_id}"
            timedtext_response = requests.get(timedtext_url)
            
            if timedtext_response.status_code == 200 and timedtext_response.text:
                # Parse the XML response
                xml_content = timedtext_response.text
                # Extract text from XML using regex
                text_parts = re.findall(r'<text[^>]*>(.*?)</text>', xml_content)
                
                # Clean up HTML entities
                cleaned_parts = [html.unescape(part) for part in text_parts]
                transcript_text = " ".join(cleaned_parts)
                
                if transcript_text:
                    print("Successfully extracted transcript from timedtext API")
                    return jsonify({
                        "video_id": video_id,
                        "captions": transcript_text
                    })
                
            return jsonify({"error": "No captions available for this video"}), 404
        
        # Step 2: Download the caption track
        # Note: This requires auth with OAuth 2.0, not just an API key
        # For simplicity, we'll use the timedtext API instead
        
        timedtext_url = f"https://www.youtube.com/api/timedtext?lang=en&v={video_id}"
        print(f"Fetching caption content from timedtext API")
        
        timedtext_response = requests.get(timedtext_url)
        
        if timedtext_response.status_code != 200 or not timedtext_response.text:
            print("Failed to fetch captions from timedtext API")
            return jsonify({"error": "Failed to fetch caption content"}), 500
        
        # Parse the XML response
        xml_content = timedtext_response.text
        # Extract text from XML using regex
        text_parts = re.findall(r'<text[^>]*>(.*?)</text>', xml_content)
        
        # Clean up HTML entities
        cleaned_parts = [html.unescape(part) for part in text_parts]
        transcript_text = " ".join(cleaned_parts)
        
        if not transcript_text:
            print("No text content found in captions")
            return jsonify({"error": "No text content in captions"}), 404
        
        print(f"Successfully extracted transcript with {len(cleaned_parts)} segments")
        
        # Return JSON with "captions" so Tana can map it into the Captions field
        return jsonify({
            "video_id": video_id,
            "captions": transcript_text
        })

    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
