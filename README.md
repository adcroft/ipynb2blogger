# ipynb2blogger

A tool for posting iPython notebooks to blogger

## Pre-requisites

- The google API python client library. See https://developers.google.com/api-client-library/python/.
- An "installed application" client ID. See https://console.developers.google.com/project
- A blog on blogger/blogspot wiht "Site feed" set to full.

## Installation

- Download _client_secrets.json_ from your google console and place in the same directory as `ipynb2blogger.py`.
- Make sure you have pip: `apt-get install python-pip`
- Install google's python api-client-library: `pip install --upgrade google-api-python-client`

## Authenticating

The first time you run ipynb2blogger.py the script will connect to the blogger API which will ask for you to sign-in via a browser. Sign-in and then click "accept" to have a token sent back to the script to use to reach your blogger account. The token is stored in a file local to where you ran ipynb2blogger.py.
