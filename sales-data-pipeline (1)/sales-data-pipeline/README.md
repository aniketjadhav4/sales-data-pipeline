## How to Run

### 1. Clone the repository

```bash
git clone https://github.com/aniketjadhav4/sales-data-pipeline.git
cd sales-data-pipeline
```

Navigate into the folder containing `generate_data.py`, `etl.py`, and `requirements.txt` before continuing.

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Generate synthetic sales data

```bash
python generate_data.py
```

### 4. Run the ETL pipeline

```bash
python etl.py
```

### 5. Run SQL analysis and export results

```bash
python run_analysis.py
```

### Expected outputs

After a successful run, verify that the project generates the warehouse database, rejected-records file, ETL summary, and Power BI CSV exports described above.

**Note:** Run each command separately and confirm that the previous step succeeds before proceeding. The exact paths and commands may need adjustment to match the repository's folder structure.
