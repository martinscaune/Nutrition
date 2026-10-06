# Raw data manifest

Raw files are stored **unmodified**. Large files are git-ignored (see `.gitignore`) and can be re-downloaded from the URL below; verify them with the checksum.

| Dataset | Local path | Source URL | Downloaded | SHA-256 | License | In git? |
|---|---|---|---|---|---|---|
| USDA FoodData Central, SR Legacy (April 2018 release, CSV) | `data/raw/usda/sr_legacy_csv.zip` (extracted to `data/raw/usda/sr_legacy/`) | https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip | 2026-10-06 | `b80817294b8850530aaedf2e515c02593b1824f763a0ff356e5c2081643e6fd0` | Public domain (USDA) | no (6 MB zip / 40 MB extracted) |
| Muleya & Salter (2021), Ileal amino acid digestibility and DIAAS values of world foods, v1 | `data/raw/muleya2021/muleya2021_diaas.xlsx` | https://data.mendeley.com/datasets/gz3cx7d5f4/1 (DOI 10.17632/gz3cx7d5f4.1) | 2026-10-06 | `e7a1135e88772f8745577ce0a311e1aad16bd7a6b9647dff0872f74946f48e01` | CC BY 4.0 (attribution required) | yes (411 kB) |

## Known issues found so far
- **SR Legacy amino-acid profiles:** some are implausible (ground beef 80/20 and plain whole-milk yogurt Trp ≈ 5 mg/g protein; firm tofu Cys 3.3 mg/g), and some entries have none (pollock, kefir, white bread). See PLAN task 2.16.
- **muleya2021:** 290 rows, most of them animal-feed ingredients; per-AA digestibility comes from pig, human or human-predicted models (column "Model"); some DIAAS are blank where data were incomplete. There are no whole-fish food entries (only fish meal), and chicken and egg have digestibility values but no DIAAS.
