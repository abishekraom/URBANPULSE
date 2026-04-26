#!/bin/bash

# Renders the Remotion video
# Usage: ./render_video.sh <output_name>

OUTPUT_NAME=${1:-"out.mp4"}

echo "Rendering video to $OUTPUT_NAME on Desktop..."

# Assuming project structure is set up where "RemotionVideo" is the composition ID
# You might need to adjust "RemotionVideo" based on what is registered in Root.tsx

npx remotion render RemotionVideo "C:/Users/${USER}/Desktop/$OUTPUT_NAME"

echo "Render complete: C:/Users/${USER}/Desktop/$OUTPUT_NAME"
