#!/bin/bash
# Render Start Script
python -m uvicorn main:app --host 0.0.0.0 --port $PORT
