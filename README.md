# Quantitative Food Value for Training

Personal computational-nutrition project: which foods (and later, which food combinations) give the most
useful protein, calories and carbohydrate per euro and per gram eaten, for any training goal.

- **What and why:** [PROJECT.md](PROJECT.md) · **Tasks and progress:** [PLAN.md](PLAN.md)
- **Evidence base:** [literature/REVIEW.md](literature/REVIEW.md) · **Data rules:** [data/SCHEMA.md](data/SCHEMA.md)
- **Technical report:** [reports/technical_report.md](reports/technical_report.md)
- **Latest results:** [reports/v2.0_nutrients.md](reports/v2.0_nutrients.md) (complete diets), [reports/v1.0_optimizer.md](reports/v1.0_optimizer.md) (diets), [reports/scenarios_v0.2.md](reports/scenarios_v0.2.md) (profiles), [reports/v0.1_exploration.md](reports/v0.1_exploration.md) (foods)

## Run the app
Tabs: targets & AI export · **rate & improve a meal** · diet optimizer (minimum or realistic, split into meals) · fix
my usual day · rankings · explorer · food details. The country for prices is chosen in the upper right (Latvia observed;
other EU countries ≈ via Eurostat price levels). Share it privately with friends: [DEPLOY.md](DEPLOY.md).
```sh
# inside the VS Code (Flatpak) terminal:
host-spawn .venv/bin/streamlit run app/app.py --server.address localhost
# in a normal terminal:
.venv/bin/streamlit run app/app.py --server.address localhost
```
Opens http://localhost:8501 (bound to this computer by `--server.address localhost`).

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
.venv/bin/python src/analysis/robustness.py  # → reports/v1x_robustness.md
.venv/bin/python src/analysis/comparison.py  # → reports/v1x_comparison.md
.venv/bin/python src/analysis/v2_report.py   # → reports/v2.0_nutrients.md
.venv/bin/python -m pytest -q                 # tests
```
Export a person-specific ranking + AI brief (also in the app, tab "My targets & AI export"):
`.venv/bin/python -m src.export --profile config/profiles/owner.yaml --country DK` → `exports/…/` (foods_ranked.csv,
optimal_diet.csv, realistic_diet.csv with a meal split, brief.md)

Refresh prices from Cenu Depo (polite, ≥ 3 s between requests): `python3 -m src.prices.cenudepo`.

## Data licences
Frida 5.5 (CC BY 4.0, DTU Food) · EFSA DRV and UL documents (reproduction authorised with acknowledgement) · USDA FoodData Central (public domain) · muleya2021 DIAAS dataset (CC BY 4.0) ·
CSP Latvia PCC010m (open data) · Eurostat price level indices (free re-use with acknowledgement) ·
**Cenu Depo prices: personal use only**, not for publication without permission (keep shared apps private).
