from flask import Flask, request, jsonify
import os
import requests
import html
import re

app = Flask(__name__)

# Your YouTube API key
YOUTUBE_API_KEY = "AIzaSyBQEL9ZNU7tlgsSte4362v5TsxYrsvo308"  # Replace with your actual API key

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
        caption_type = None
        for item in captions_data.get('items', []):
            language = item.get('snippet', {}).get('language', '')
            track_kind = item.get('snippet', {}).get('trackKind', '')
            
            if language == 'en' or language.startswith('en-'):
                caption_id = item.get('id')
                caption_type = track_kind
                print(f"Found English caption track: {caption_id}, type: {track_kind}")
                break
        
        transcript_text = None
        
        if caption_id:
            # Try multiple methods to get the transcript
            
            # Method 1: Standard timedtext API
            timedtext_url = f"https://www.youtube.com/api/timedtext?lang=en&v={video_id}"
            print(f"Trying Method 1: Standard timedtext API")
            timedtext_response = requests.get(timedtext_url)
            
            if timedtext_response.status_code == 200 and timedtext_response.text and "<text" in timedtext_response.text:
                print("Method 1 succeeded")
                # Parse the XML response
                xml_content = timedtext_response.text
                # Extract text from XML using regex
                text_parts = re.findall(r'<text[^>]*>(.*?)</text>', xml_content)
                
                # Clean up HTML entities
                cleaned_parts = [html.unescape(part) for part in text_parts]
                transcript_text = " ".join(cleaned_parts)
            else:
                # Method 2: Try with caption track ID
                timedtext_url = f"https://www.youtube.com/api/timedtext?type=track&v={video_id}&id={caption_id}"
                print(f"Trying Method 2: Timedtext API with track ID")
                timedtext_response = requests.get(timedtext_url)
                
                if timedtext_response.status_code == 200 and timedtext_response.text and "<text" in timedtext_response.text:
                    print("Method 2 succeeded")
                    # Parse the XML response
                    xml_content = timedtext_response.text
                    # Extract text from XML using regex
                    text_parts = re.findall(r'<text[^>]*>(.*?)</text>', xml_content)
                    
                    # Clean up HTML entities
                    cleaned_parts = [html.unescape(part) for part in text_parts]
                    transcript_text = " ".join(cleaned_parts)
                else:
                    # Method 3: Try with ASR format
                    timedtext_url = f"https://www.youtube.com/api/timedtext?fmt=srv3&v={video_id}&asr_langs=en&key=yttt1"
                    print(f"Trying Method 3: Timedtext API with ASR format")
                    timedtext_response = requests.get(timedtext_url)
                    
                    if timedtext_response.status_code == 200 and timedtext_response.text:
                        print("Method 3 succeeded")
                        # This format might be different (JSON or XML)
                        content_type = timedtext_response.headers.get('Content-Type', '')
                        
                        if 'xml' in content_type or '<text' in timedtext_response.text:
                            # XML format
                            xml_content = timedtext_response.text
                            text_parts = re.findall(r'<text[^>]*>(.*?)</text>', xml_content)
                            cleaned_parts = [html.unescape(part) for part in text_parts]
                            transcript_text = " ".join(cleaned_parts)
                        elif 'json' in content_type:
                            # JSON format
                            try:
                                json_data = timedtext_response.json()
                                # Extract text based on JSON structure
                                # This is a simplified version and might need adjusting based on actual format
                                if 'events' in json_data:
                                    text_parts = []
                                    for event in json_data['events']:
                                        if 'segs' in event:
                                            for seg in event['segs']:
                                                if 'utf8' in seg:
                                                    text_parts.append(seg['utf8'])
                                    transcript_text = " ".join(text_parts)
                            except:
                                print("Failed to parse JSON response")
                    else:
                        # Method 4: Try with formats param
                        timedtext_url = f"https://www.youtube.com/api/timedtext?v={video_id}&lang=en&fmt=json3"
                        print(f"Trying Method 4: Timedtext API with JSON format")
                        timedtext_response = requests.get(timedtext_url)
                        
                        if timedtext_response.status_code == 200 and timedtext_response.text:
                            print("Method 4 succeeded")
                            try:
                                json_data = timedtext_response.json()
                                # Extract text based on JSON structure
                                if 'events' in json_data:
                                    text_parts = []
                                    for event in json_data['events']:
                                        if 'segs' in event:
                                            for seg in event['segs']:
                                                if 'utf8' in seg:
                                                    text_parts.append(seg['utf8'])
                                    transcript_text = " ".join(text_parts)
                            except:
                                print("Failed to parse JSON response")
        else:
            # No captions found through the API, try a direct approach
            print("No caption tracks found, trying direct timedtext API")
            
            # Try the timedtext API directly
            timedtext_url = f"https://www.youtube.com/api/timedtext?lang=en&v={video_id}"
            timedtext_response = requests.get(timedtext_url)
            
            if timedtext_response.status_code == 200 and timedtext_response.text and "<text" in timedtext_response.text:
                # Parse the XML response
                xml_content = timedtext_response.text
                # Extract text from XML using regex
                text_parts = re.findall(r'<text[^>]*>(.*?)</text>', xml_content)
                
                # Clean up HTML entities
                cleaned_parts = [html.unescape(part) for part in text_parts]
                transcript_text = " ".join(cleaned_parts)
        
        if not transcript_text:
            print("All methods failed to retrieve transcript")
            return jsonify({"error": "Could not retrieve transcript content"}), 404
        
        print(f"Successfully extracted transcript")
        
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
