## Argument Miner

- Argument Miner is a Flask web app for uploading text-based PDF documents, extracting key arguments using the Grok API, and downloading outputs as .txt or .doc files. It features a clean, light-themed interface.

## Sample Image
![image alt](https://github.com/shahil5z/Argument-Miner/blob/9e71bbcfa516fc702229ebc8c7b66acb50a06930/SAMPLE_1.png)

## Features

- Upload text-based PDFs for processing.
- Choose .txt or .doc output format.
- Extracts arguments via Grok API.
- View and download processed files from saved.arg.
- Light theme with clear text visibility.

## Configure API

- Add GROQ_API_KEY to .env

## Install packages

- pip install -r requirements.txt

## Run the App

- python app.py

## Notes

- Only text-based PDFs are supported.
- Outputs are saved in saved.arg.
- Check app.log for errors if no files appear.
