#!/usr/bin/env python3
"""
DesiYatra - Google Cloud Platform Setup Script
Automates GCP project configuration for cross-platform compatibility
"""
import subprocess
import sys
import os
import json
from pathlib import Path

def run_command(cmd, check=True):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stderr.strip(), e.returncode

def check_gcloud():
    """Check if gcloud CLI is installed"""
    _, code = run_command("gcloud --version", check=False)
    return code == 0

def main():
    print("🚀 DesiYatra - Google Cloud Platform Setup")
    print("=" * 50)
    print()
    
    # Check gcloud installation
    if not check_gcloud():
        print("❌ gcloud CLI not found. Please install it first:")
        print("   https://cloud.google.com/sdk/docs/install")
        sys.exit(1)
    
    # Get project ID
    project_id = input("Enter your GCP Project ID (or press Enter to use current): ").strip()
    if not project_id:
        output, _ = run_command("gcloud config get-value project")
        project_id = output
    
    if not project_id:
        print("❌ No project ID provided or configured")
        sys.exit(1)
    
    print(f"📋 Using Project: {project_id}")
    print()
    
    # Set project
    print("🔧 Setting active project...")
    run_command(f"gcloud config set project {project_id}")
    print("✅ Project set")
    print()
    
    # Enable APIs
    print("🔧 Enabling required APIs (this may take a few minutes)...")
    apis = [
        "aiplatform.googleapis.com",
        "firestore.googleapis.com",
        "speech.googleapis.com",
        "bigquery.googleapis.com",
        "generativelanguage.googleapis.com"
    ]
    
    for api in apis:
        print(f"   Enabling {api}...")
        run_command(f"gcloud services enable {api} --project={project_id}")
    
    print("✅ APIs enabled")
    print()
    
    # Setup Firestore
    print("🗄️ Setting up Firestore...")
    output, code = run_command(f"gcloud firestore databases describe --project={project_id}", check=False)
    
    if code == 0:
        print("✅ Firestore already exists")
    else:
        location = input("Select Firestore location (default: asia-south1): ").strip() or "asia-south1"
        run_command(f"gcloud firestore databases create --location={location} --type=firestore-native --project={project_id}")
        print("✅ Firestore created")
    print()
    
    # Create service account
    print("🔑 Creating service account...")
    sa_name = "desiyatra-agent"
    sa_email = f"{sa_name}@{project_id}.iam.gserviceaccount.com"
    
    output, code = run_command(f"gcloud iam service-accounts describe {sa_email} --project={project_id}", check=False)
    
    if code == 0:
        print("✅ Service account already exists")
    else:
        run_command(f'gcloud iam service-accounts create {sa_name} --display-name="DesiYatra Agent Service Account" --project={project_id}')
        print("✅ Service account created")
    print()
    
    # Grant permissions
    print("🔐 Granting permissions...")
    roles = [
        "roles/aiplatform.user",
        "roles/datastore.user",
        "roles/speech.client",
        "roles/bigquery.dataViewer"
    ]
    
    for role in roles:
        run_command(f'gcloud projects add-iam-policy-binding {project_id} --member="serviceAccount:{sa_email}" --role="{role}" --condition=None', check=False)
    
    print("✅ Permissions granted")
    print()
    
    # Create service account key
    print("🔑 Creating service account key...")
    key_file = "gcp-credentials.json"
    
    if os.path.exists(key_file):
        overwrite = input(f"⚠️  {key_file} already exists. Overwrite? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("Skipping key creation")
        else:
            run_command(f"gcloud iam service-accounts keys create {key_file} --iam-account={sa_email} --project={project_id}")
            print(f"✅ Key created: {key_file}")
    else:
        run_command(f"gcloud iam service-accounts keys create {key_file} --iam-account={sa_email} --project={project_id}")
        print(f"✅ Key created: {key_file}")
    print()
    
    # Get Gemini API key
    print("🔑 Getting Gemini API Key...")
    print("⚠️  You need to create this manually at:")
    print("   https://aistudio.google.com/app/apikey")
    print()
    gemini_key = input("Enter your Gemini API Key: ").strip()
    print()
    
    # Update .env file
    print("📝 Updating .env file...")
    env_path = Path(".env")
    
    if env_path.exists():
        # Backup
        import shutil
        shutil.copy(env_path, ".env.backup")
        print("✅ Backed up existing .env to .env.backup")
        
        # Read existing
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Remove old GCP config
        lines = [l for l in lines if not any(k in l for k in ['GOOGLE_CLOUD_PROJECT', 'GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_API_KEY'])]
    else:
        lines = []
    
    # Append new config
    lines.append("\n# Google Cloud Configuration (Auto-generated by setup_gcp.py)\n")
    lines.append(f"GOOGLE_CLOUD_PROJECT={project_id}\n")
    lines.append(f"GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json\n")
    lines.append(f"GOOGLE_API_KEY={gemini_key}\n")
    
    with open(env_path, 'w') as f:
        f.writelines(lines)
    
    print("✅ .env file updated")
    print()
    
    # Summary
    print("=" * 50)
    print("✅ GCP Setup Complete!")
    print("=" * 50)
    print()
    print("📋 Summary:")
    print(f"  Project ID: {project_id}")
    print(f"  Service Account: {sa_email}")
    print(f"  Credentials: {key_file}")
    print()
    print("🔧 Enabled Services:")
    print("  ✓ Vertex AI (Gemini, Vector Search)")
    print("  ✓ Firestore (State Management)")
    print("  ✓ Speech-to-Text (Voice Recognition)")
    print("  ✓ BigQuery (Vendor History)")
    print()
    print("📝 Next Steps:")
    print("  1. Review your .env file")
    print("  2. Run: docker-compose up --build")
    print("  3. (Optional) Setup Vector Search: python scripts/setup_vector_search.py")
    print()
    print("⚠️  Security Note:")
    print("  - Keep gcp-credentials.json secure")
    print("  - Add it to .gitignore (already done)")
    print("  - Never commit it to version control")
    print()

if __name__ == "__main__":
    main()
