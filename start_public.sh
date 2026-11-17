#!/bin/bash
# Starts the app and a free Cloudflare tunnel, prints the public links. Stop everything with Ctrl+C.
cd "$(dirname "$0")"                                                   # run from the app folder
streamlit run app.py --server.headless true > streamlit.log 2>&1 &     # app on localhost:8501 in the background
APP=$!                                                                 # its process id
cloudflared tunnel --url http://localhost:8501 > tunnel.log 2>&1 &     # public https tunnel to the app
TUN=$!                                                                 # its process id
trap 'kill $APP $TUN 2>/dev/null; exit' INT TERM                       # Ctrl+C stops both
for i in $(seq 60); do                                                 # wait up to 60 s for the link
  URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' tunnel.log | head -1)
  [ -n "$URL" ] && break; sleep 1
done
echo "========================================"
echo " Phones:       $URL/phone"                                       # link for everyone / QR code (light, 4 s)
echo " TV:           $URL/tv"
echo " Admin:        $URL/admin   (password protected)"                # link for you
echo " Local:        http://localhost:8501/admin"
echo "========================================"
wait                                                                   # keep running until Ctrl+C
