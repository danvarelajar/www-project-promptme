#!/bin/bash
# Restart PromptMe server
cd "$(dirname "$0")"
./stop.sh
sleep 2
./start.sh
