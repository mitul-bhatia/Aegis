#!/bin/bash
# Simple backend startup without scheduler
export ENABLE_AUTONOMOUS_SCANNING=false
source .venv/bin/activate
python main.py
