# Gerber to STL Converter

This project provides a web interface for converting Gerber PCB layout files into 3D STL models using OpenSCAD.  
It uses a Dash (Flask) backend with file upload, server-side conversion, and download.

## 🔧 Features

- Upload `.gbr` or `.zip` Gerber files
- Convert to `.stl` using OpenSCAD
- Download the STL for 3D printing or preview
- Runs serverlessly on Google Cloud Run

## 🐍 Local Development

### Prerequisites

- Python 3.8+
- OpenSCAD (CLI)
- Flask / Dash

### Run Locally

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:8080

## Testing the docker image locally
### Docker build & Run
```bash
docker build -t gerb2svg .
docker run --rm -it -p8080:8080 gerb2svg
```

Then open http://localhost:8080

## ☁️ Deploying to Google Cloud Run

### Step 1: Set up Google Cloud Project

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### Step 2: Build & Deploy

Make sure `cloudbuild.yaml`, `app.py`, and `Dockerfile` are in the root directory.

```bash
gcloud builds submit --config cloudbuild.yaml
```

This will:
- Build the Docker image
- Push it to Container/Artifact Registry
- Deploy to Cloud Run as a public HTTPS service

### Optional: Make it Public (if not already)

```bash
gcloud run services add-iam-policy-binding openscad-service \
  --region us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker"
```

## 🧠 File Structure

```
.
├── app.py              # Main Dash/Flask web app
├── converter.py        # Contains gerber_to_stl() logic
├── Dockerfile          # Runtime environment with OpenSCAD + Python
├── cloudbuild.yaml     # CI/CD deployment config
└── assets/             # Optional CSS, screenshots, etc.
```

## 📎 License

MIT — use it freely.
