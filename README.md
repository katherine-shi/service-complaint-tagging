# Vehicle Service Complaint Tagging

A small pipeline that turns free-text vehicle complaints into structured, service-oriented tags with an LLM, checks the tags against an independent label, and produces a summary report automatically.

## Why

Service teams collect large volumes of free-text feedback. Manual tagging is slow and inconsistent, which makes it hard to see which vehicle systems drive service demand and cost. This project tests whether an LLM can do the tagging reliably, using public data where an independent label exists to measure it.

## Data

Owner complaints from the public [NHTSA complaints API](https://api.nhtsa.gov/complaints/complaintsByVehicle?make=tesla&model=model%203&modelYear=2022) for Tesla Model 3 and Model Y, model years 2021-2024. Each record has the owner's free-text summary and NHTSA's own component label. Complaints are unverified consumer reports.

## Pipeline

| Step | What it does | Code |
| --- | --- | --- |
| 1. Fetch | Pulls complaints from the API into SQLite | `src/fetch.py` |
| 2. Tag | LLM reads each summary and returns JSON: vehicle system, failure type, severity, whether a service visit happened, and any repair cost the owner states. Replies are validated against the allowed values and retried if invalid | `src/tag.py` |
| 3. Evaluate | Compares the LLM's category with NHTSA's component label. The LLM never sees that label | `src/evaluate.py` |
| 4. Report | Runs the SQL in `sql/analysis.sql` and writes `reports/report.md` with a chart | `src/report.py` |

Tagging is resumable: each run only tags complaints that have no tag yet.

## Results

- Sample size: **2,103 complaints** (all fetched complaints; 1,285 tagged by `deepseek-flash` through the pipeline, the remaining 818 by `claude-opus-5-5` after the DeepSeek account ran out of credit)
- Accuracy: **81.0%**, measured as agreement with NHTSA's component labels (`deepseek-flash` 75.7%, `claude-opus-5-5` 89.2%; the two taggers saw different, non-random subsets, so their rates are not directly comparable). NHTSA labels are a reference, not ground truth, so this is a proxy for accuracy
- Largest category: **Driver assistance & software, 1,351 complaints (64.2%)**, 84.4% of them safety-critical; most describe phantom braking
- Weakest agreement: Battery, charging & propulsion (37%) and Electrical & electronics (46%), mostly unintended-acceleration and loss-of-power complaints that NHTSA files under different components

See [`reports/report.md`](reports/report.md) for the full output.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env        # add your API key; any OpenAI-compatible endpoint works
python run.py fetch         # about 1 minute
python run.py tag --limit 300
python run.py report
```

`python -m pytest` runs offline tests on synthetic records. `--mock` swaps the LLM for a keyword tagger so the pipeline can be tested without an API key; it is not used for results.

## Limitations

- NHTSA labels are assigned from the complaint form, not by a technician, so they are a reference point rather than ground truth.
- A complaint can carry several NHTSA components while the LLM picks one primary system; agreement counts a match with any of them.
- Repair cost covers only complaints where the owner states an amount.
