from flask import Flask, request, jsonify
import os
import requests
import json
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
        print(f"Processing transcript for video ID: {video_id}")
        
        # Try using InvidiousAPI - a proxy service that can fetch YouTube data
        print("Attempting to use Invidious API to fetch captions")
        
        # Using a public Invidious instance to bypass YouTube restrictions
        # List of instances: https://api.invidious.io/
        invidious_instances = [
            "https://invidious.snopyta.org",
            "https://invidious.kavin.rocks",
            "https://vid.puffyan.us",
            "https://yt.artemislena.eu",
            "https://invidious.flokinet.to"
        ]
        
        transcript_text = None
        error_messages = []
        
        # Try each instance until we get a successful response
        for instance in invidious_instances:
            try:
                print(f"Trying Invidious instance: {instance}")
                captions_url = f"{instance}/api/v1/captions/{video_id}"
                captions_response = requests.get(captions_url, timeout=10)
                
                if captions_response.status_code == 200:
                    captions_data = captions_response.json()
                    print(f"Captions data received: {len(captions_data)} caption tracks found")
                    
                    # Look for English captions
                    english_caption = None
                    for caption in captions_data:
                        if caption.get('languageCode') == 'en' or caption.get('language_code') == 'en':
                            english_caption = caption
                            break
                    
                    if not english_caption:
                        print("No English captions found")
                        error_messages.append(f"No English captions found on {instance}")
                        continue
                    
                    # Get the caption URL
                    if 'url' in english_caption:
                        caption_url = english_caption['url']
                    elif 'baseUrl' in english_caption:
                        caption_url = english_caption['baseUrl']
                    else:
                        print("Could not find caption URL")
                        error_messages.append(f"No caption URL found on {instance}")
                        continue
                    
                    # Make sure we have a full URL
                    if not caption_url.startswith('http'):
                        caption_url = f"{instance}{caption_url}"
                    
                    print(f"Fetching caption content from: {caption_url}")
                    transcript_response = requests.get(caption_url, timeout=10)
                    
                    if transcript_response.status_code == 200:
                        # Process the transcript content based on format
                        content_type = transcript_response.headers.get('Content-Type', '')
                        
                        if 'json' in content_type:
                            # Handle JSON format
                            transcript_data = transcript_response.json()
                            
                            # Extract text based on JSON structure
                            transcript_parts = []
                            if 'events' in transcript_data:
                                for event in transcript_data['events']:
                                    if 'segs' in event:
                                        for seg in event['segs']:
                                            if 'utf8' in seg:
                                                text = seg['utf8'].strip()
                                                if text:
                                                    transcript_parts.append(text)
                            
                            transcript_text = " ".join(transcript_parts)
                            
                        elif 'xml' in content_type or 'ttml' in content_type:
                            # Handle XML/TTML format
                            xml_content = transcript_response.text
                            # Extract text from XML using regex
                            text_parts = re.findall(r'<text[^>]*>(.*?)</text>', xml_content)
                            transcript_text = " ".join(text_parts)
                            
                        else:
                            # Handle plain text or other formats
                            transcript_text = transcript_response.text
                            # Clean up any XML/HTML tags
                            transcript_text = re.sub(r'<[^>]+>', '', transcript_text)
                        
                        # If we got a transcript, break the loop
                        if transcript_text:
                            print(f"Successfully extracted transcript from {instance}")
                            break
                    else:
                        print(f"Failed to fetch caption content: {transcript_response.status_code}")
                        error_messages.append(f"Caption content request failed with status {transcript_response.status_code} on {instance}")
                        
                else:
                    print(f"Failed to fetch captions data: {captions_response.status_code}")
                    error_messages.append(f"Captions data request failed with status {captions_response.status_code} on {instance}")
            
            except Exception as instance_error:
                print(f"Error with instance {instance}: {str(instance_error)}")
                error_messages.append(f"Error with {instance}: {str(instance_error)}")
        
        # If we still don't have a transcript, try one more approach - YouTube's API
        if not transcript_text:
            print("Trying YouTube Data API approach")
            # Note: This would require an API key, which I'm not including here
            # You would need to create a project in Google Cloud Console and get a YouTube Data API key
            # Then you could use this to fetch captions
            
            # For now, return error if no transcript was found
            print("All methods failed to retrieve transcript")
            return jsonify({
                "error": "Could not retrieve transcript", 
                "details": error_messages
            }), 404
        
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
