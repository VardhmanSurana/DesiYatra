# Kaggle Agents Intensive Capstone Project - Submission Guide

This guide will help you submit your **DesiYatra** project to the [Kaggle Agents Intensive Capstone Project](https://www.kaggle.com/competitions/agents-intensive-capstone-project/code).

## ✅ Pre-Submission Checklist

1.  **Code Cleanup**: I have verified that your code does **not** contain hardcoded API keys (checked for `API_KEY`, `sk-`, `TWILIO`, `SARVAM`).
2.  **README.md**: Your `README.md` is excellent and covers the required sections (Problem, Solution, Architecture, Setup).
3.  **Zip Archive**: A submission archive `desiyatra_submission.zip` has been created in your project root, excluding sensitive files like `.env` and `.venv`.

---

## 🚀 Option 1: Submit via GitHub (Recommended)

This is the cleanest way to submit your project.

1.  **Create a GitHub Repository**:
    - If you haven't already, create a new public repository on GitHub.
    - Initialize git in your project folder if needed:
      ```bash
      git init
      git add .
      git commit -m "Initial commit for Kaggle Capstone"
      git branch -M main
      git remote add origin <your-repo-url>
      git push -u origin main
      ```

2.  **Submit via Writeup**:
    - Go to the [Competition Page](https://www.kaggle.com/competitions/agents-intensive-capstone-project).
    - Look for a **"New Writeup"** or **"Submit"** button (often found under the "Overview" or "Discussion" tabs, or as a primary action button).
    - **Fill in the Form**:
        - **Title**: DesiYatra - AI Travel Negotiation Agent
        - **Subtitle**: AI-powered travel negotiation agents that find local vendors, call them, and negotiate prices in Hindi/Hinglish.
        - **Track**: Select the appropriate track (e.g., "Concierge Agents" or "Freestyle").
        - **Attachments**: Paste the link to your **GitHub Repository**.
        - **Description**: Copy the contents of your `README.md` (Problem, Solution, Architecture).
        - **Video**: (Optional) Add a YouTube link if you have one.

---

## 📝 Option 2: Submit via Kaggle Notebook

If you prefer to host everything on Kaggle:

1.  **Create a New Notebook**:
    - Go to the [Code tab](https://www.kaggle.com/competitions/agents-intensive-capstone-project/code).
    - Click **"New Notebook"**.

2.  **Upload Your Code**:
    - In the Notebook editor, look for the **"Input"** section on the right sidebar.
    - Click **"Upload"** -> **"New Dataset"**.
    - Drag and drop the `desiyatra_submission.zip` file I created for you.
    - Name the dataset (e.g., `desiyatra-source`).
    - Click **"Create"**.

3.  **Setup the Notebook**:
    - Once the dataset is uploaded, it will be available at `/kaggle/input/desiyatra-source`.
    - Use the following code in your notebook cells to set up and run your agent:

    ```python
    # Cell 1: Setup
    import os
    import shutil

    # Copy files to working directory (since input is read-only)
    if not os.path.exists("/kaggle/working/desiyatra"):
        shutil.unpack_archive("/kaggle/input/desiyatra-source/desiyatra_submission.zip", "/kaggle/working/desiyatra")

    os.chdir("/kaggle/working/desiyatra")
    
    # Install dependencies
    !pip install -r requirements.txt
    !pip install uv
    ```

    ```python
    # Cell 2: Set Environment Variables
    # IMPORTANT: Use Kaggle Secrets for API keys!
    # Go to "Add-ons" -> "Secrets" in the notebook menu to add your keys.
    
    from kaggle_secrets import UserSecretsClient
    user_secrets = UserSecretsClient()
    
    os.environ["GOOGLE_API_KEY"] = user_secrets.get_secret("GOOGLE_API_KEY")
    os.environ["TWILIO_ACCOUNT_SID"] = user_secrets.get_secret("TWILIO_ACCOUNT_SID")
    # ... add other secrets as needed
    ```

    ```python
    # Cell 3: Run a Demo
    # Run your test script or main agent
    !python tests/test_refactored_agents.py
    ```

4.  **Save and Submit**:
    - Click **"Save Version"** (Save & Run All).
    - Once saved, make the notebook **Public** (Share -> Public).
    - **Go to the Competition Page** and click **"New Writeup"**.
    - Fill in the details (Title, Subtitle, Track).
    - **Attachments**: Select "Kaggle Notebook" and choose your `desiyatra-submission` notebook.
    - **Description**: Copy your `README.md` content.

---

## 📄 Required Submission Details

When submitting, ensure you provide:

*   **Project Title**: DesiYatra - AI Travel Negotiation Agent
*   **Tagline**: AI-powered travel negotiation agents that find local vendors, call them, and negotiate prices in Hindi/Hinglish.
*   **Description**: (Copy the "Overview" and "Key Features" from your `README.md`).
*   **Video (Optional)**: If you have a demo video, upload it to YouTube and link it.

Good luck! 🇮🇳
