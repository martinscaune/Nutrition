# Quantitative Food Value for Training

Personal computational-nutrition project: which foods (and later, which food combinations) give the most
useful protein, calories and carbohydrate per euro and per gram eaten, for any training goal.

- **What and why:** [PROJECT.md](PROJECT.md) · **Tasks and progress:** [PLAN.md](PLAN.md)
- **Evidence base:** [literature/REVIEW.md](literature/REVIEW.md) · **Data rules:** [data/SCHEMA.md](data/SCHEMA.md)
- **Technical report:** [reports/technical_report.md](reports/technical_report.md)
- **Latest results:** [reports/v1.0_optimizer.md](reports/v1.0_optimizer.md) (diets), [reports/scenarios_v0.2.md](reports/scenarios_v0.2.md) (profiles), [reports/v0.1_exploration.md](reports/v0.1_exploration.md) (foods)

## Run the food explorer (v0.1)
```sh
# inside the VS Code (Flatpak) terminal:
host-spawn .venv/bin/streamlit run app/app.py
# in a normal terminal:
.venv/bin/streamlit run app/app.py
```
Opens http://localhost:8501 (local only; see `.streamlit/config.toml`).

## Rebuild everything from raw data
`sh run_all.sh` (inside the Flatpak terminal: `host-spawn sh run_all.sh`) runs all steps below in < 1 minute.
```sh
.venv/bin/python src/data/resolve.py          # composition + yields → data/processed/composition_resolved.csv
.venv/bin/python src/prices/summary.py        # prices → data/processed/prices_summary.csv
.venv/bin/python src/build_master.py          # → data/processed/foods_master.csv (input to everything)
.venv/bin/python src/analysis/explore.py      # → reports/v0.1_exploration.md
.venv/bin/python src/analysis/figures.py      # → figures/v0.1/*.png
.venv/bin/python src/analysis/scenarios.py    # → reports/scenarios_v0.2.md
.venv/bin/python src/analysis/optimize_report.py  # → reports/v1.0_optimizer.md, figures/v1.0/
.venv/bin/python -m pytest -q                 # tests
```
Export a person-specific ranking + AI brief (also in the app, tab "My targets & AI export"):
`.venv/bin/python -m src.export --profile config/profiles/owner.yaml --preset "Bulking: balanced"` → `exports/…/`

Refresh prices from Cenu Depo (polite, ≥ 3 s between requests): `python3 -m src.prices.cenudepo`.

## Data licences
Frida 5.5 (CC BY 4.0, DTU Food) · USDA FoodData Central (public domain) · muleya2021 DIAAS dataset (CC BY 4.0) ·
CSP Latvia PCC010m (open data) · **Cenu Depo prices: personal use only**, not for publication without permission.
