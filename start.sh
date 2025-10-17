#!/bin/bash

# Ensure the instance folder exists for the database
mkdir -p instance

# Install dependencies (Render usually does this automatically via requirements.txt)
# pip install -r requirements.txt

# Start the Flask app using Waitress on the port Render provides
waitress-serve --port=$PORT app:app
