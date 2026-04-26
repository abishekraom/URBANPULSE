import argparse
import requests
import os
import time
import sys
import json

# Auphonic API endpoint
BASE_URL = "https://auphonic.com/api/production.json"

def process_audio(input_file, api_key, output_file="processed_audio.mp3"):
    if not api_key:
        print("Error: AUPHONIC_API_KEY is not set.")
        sys.exit(1)

    print(f"Creating Auphonic production for {input_file}...")
    
    # 1. Create Production
    headers = {
        "Content-Type": "application/json"
    }
    
    # Settings from instructions
    payload = {
        "api_user": "user", # Usually auth is basic auth or bearer, check specific docs. Using Basic Auth typically.
        "api_password": api_key, 
        "metadata": {"title": f"Process {os.path.basename(input_file)}"},
        "algorithms": {
            "leveler": True,
            "normloudness": True,
            "loudnesstarget": -16, # Target 16 LUFS
            "denoise": True,
            "denoisemethod": "dynamic"
        },
        "output_files": [
            {
                "format": "aac",
                "bitrate": 192
            }
        ]
    }
    
    # Note: Auphonic API typically uses Basic Auth with username/password, or Bearer token.
    # We will assume the API_KEY provided is a bearer token or we prompt user.
    # For now, implementing standard request flow.
    
    # Prepare session
    session = requests.Session()
    session.auth = (os.environ.get("AUPHONIC_USER", "user"), api_key)
    
    # Create production without file first
    response = session.post(BASE_URL, json=payload)
    if response.status_code != 200:
        print(f"Failed to create production: {response.text}")
        sys.exit(1)
        
    data = response.json()
    uuid = data["data"]["uuid"]
    print(f"Production created: {uuid}")
    
    # 2. Upload File
    # Auphonic typically expects a multipart upload to the upload_url provided or to /production/{uuid}/upload.json
    upload_url = f"https://auphonic.com/api/production/{uuid}/upload.json"
    print("Uploading file (this may take a while)...")
    with open(input_file, 'rb') as f:
        files = {'input_file': f}
        up_res = session.post(upload_url, files=files)
        if up_res.status_code != 200:
            print(f"Upload failed: {up_res.text}")
            sys.exit(1)
            
    # 3. Start Production
    start_url = f"https://auphonic.com/api/production/{uuid}/start.json"
    print("Starting processing...")
    start_res = session.post(start_url)
    if start_res.status_code != 200:
        print(f"Failed to start: {start_res.text}")
        sys.exit(1)
        
    # 4. Poll for completion
    while True:
        status_url = f"https://auphonic.com/api/production/{uuid}.json"
        status_res = session.get(status_url)
        status_data = status_res.json()
        status = status_data["data"]["status_string"]
        
        print(f"Status: {status}")
        
        if status == "Done":
            break
        elif status == "Error":
            print(f"Processing failed: {status_data['data']['error_message']}")
            sys.exit(1)
            
        time.sleep(5)
        
    # 5. Download Result
    output_url = status_data["data"]["output_files"][0]["download_url"]
    print(f"Downloading result from {output_url}...")
    
    r = session.get(output_url, stream=True)
    with open(output_file, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192): 
            f.write(chunk)
            
    print(f"Saved processed audio to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Process audio using Auphonic API")
    parser.add_argument("input_audio", help="Path to input audio/video file")
    parser.add_argument("--key", help="Auphonic API Key (or set AUPHONIC_API_KEY env var)")
    parser.add_argument("--user", help="Auphonic Username (or set AUPHONIC_USER env var)")
    parser.add_argument("--output", "-o", help="Output file path", default="processed_master.m4a")
    
    args = parser.parse_args()
    
    api_key = args.key or os.environ.get("AUPHONIC_API_KEY")
    api_user = args.user or os.environ.get("AUPHONIC_USER")
    
    if api_user:
        os.environ["AUPHONIC_USER"] = api_user
        
    process_audio(args.input_audio, api_key, args.output)

if __name__ == "__main__":
    main()
