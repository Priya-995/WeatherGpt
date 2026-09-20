# WeatherGPT

Rebuild in progress.

## Backend Setup

1. **Create Virtual Environment:**
   ```bash
   python -m venv backend/.venv
   ```

2. **Activate Virtual Environment:**
   - Windows (PowerShell):
     ```powershell
     .\backend\.venv\Scripts\Activate.ps1
     ```
   - Linux/macOS:
     ```bash
     source backend/.venv/bin/activate
     ```

3. **Install Dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Environment Configuration:**
   Copy the example environment file to `.env`:
   ```bash
   cp backend/.env.example backend/.env
   ```

5. **Run the Development Server:**
   From the `backend/` directory:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

6. **Interactive Documentation:**
   Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.

7. **Run Tests:**
   From the `backend/` directory:
   ```bash
   pytest
   ```
