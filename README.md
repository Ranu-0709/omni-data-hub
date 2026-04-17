# Omni Data Hub
This is the master repository. 

* The `frontend` folder is connected to Vercel.
* The `frontend-admin` folder runs on Google Cloud.
* The `data_generator` builds the mock CSV files.
* The `pipeline` folder holds the Airflow jobs.



# DataEngg - First Time Setup

## Prerequisites

- Python 3.8+

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:

   - **Windows (cmd):**
     ```cmd
     venv\Scripts\activate
     ```
   - **Windows (PowerShell):**
     ```powershell
     venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     source venv/bin/activate
     ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Run

```bash
python DataEngg/FolderStructure.py
```

