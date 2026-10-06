# Raw data manifest

Raw files are stored **unmodified**. Large files are git-ignored (see `.gitignore`) and can be re-downloaded from the URL below; verify them with the checksum.

| Dataset | Local path | Source URL | Downloaded | SHA-256 | License | In git? |
|---|---|---|---|---|---|---|
| USDA FoodData Central, SR Legacy (April 2018 release, CSV) | `data/raw/usda/sr_legacy_csv.zip` (extracted to `data/raw/usda/sr_legacy/`) | https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip | 2026-10-06 | `b80817294b8850530aaedf2e515c02593b1824f763a0ff356e5c2081643e6fd0` | Public domain (USDA) | no (6 MB zip / 40 MB extracted) |
| Muleya & Salter (2021), Ileal amino acid digestibility and DIAAS values of world foods, v1 | `data/raw/muleya2021/muleya2021_diaas.xlsx` | https://data.mendeley.com/datasets/gz3cx7d5f4/1 (DOI 10.17632/gz3cx7d5f4.1) | 2026-10-06 | `e7a1135e88772f8745577ce0a311e1aad16bd7a6b9647dff0872f74946f48e01` | CC BY 4.0 (attribution required) | yes (411 kB) |

## Known issues found so far
- **SR Legacy amino-acid profiles:** some are implausible (ground beef 80/20 and plain whole-milk yogurt Trp ≈ 5 mg/g protein; firm tofu Cys 3.3 mg/g), and some entries have none (pollock, kefir, white bread). See PLAN task 2.16.
- **muleya2021:** 290 rows, most of them animal-feed ingredients; per-AA digestibility comes from pig, human or human-predicted models (column "Model"); some DIAAS are blank where data were incomplete. There are no whole-fish food entries (only fish meal), and chicken and egg have digestibility values but no DIAAS.

## Added 2026-10-06
| Dataset | Local path | Source URL | Downloaded | SHA-256 | License | In git? |
|---|---|---|---|---|---|---|
| CSP (Central Statistical Bureau of Latvia) table PCC010m, average retail prices of selected commodities, all food items (codes 01.*), 2024M09–2026M08 | `data/raw/csp/PCC010m_food_last24m.csv` | PxWeb API https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/VEK/PC/PCC/PCC010m (table last updated 2026-09-08 13:00) | 2026-10-06 | `eb10d4166d622b579884bf7d6646e29e53ca21867db6eef7369c5645ce878e16` | CSP open data (cite "Central Statistical Bureau of Latvia") | yes (small) |

| Frida 5.5, Danish Food Composition Database (DTU Food) | `data/raw/frida/Frida_5.5_Dataset.xlsx` (+ English documentation PDF) | https://doi.org/10.11583/DTU.29500682.v8 (Figshare files 60901603, 60901597) | 2026-10-06 | `6b1952a35df3c0d4d7b2699ae0a3e377add42b231108309329b40256ef600e5e` (md5 b553eed6805e3cd8856663421de0f1fe as published) | CC BY 4.0 | no (12 MB) |
| USDA SR28 ASCII release (Sept 2015; for refuse % in FOOD_DES) | `data/raw/usda/sr28/sr28asc.zip` | https://www.ars.usda.gov/ARSUserFiles/80400535/DATA/SR/sr28/dnload/sr28asc.zip | 2026-10-06 | `8308fd1d224ef1e5331093748007180da01a7ac713cbac6a1f5bc2a03e1ee70a` | Public domain | no |
| Cenu Depo per-shop prices (personal-use phase only; not for publication without permission) | `data/raw/cenudepo/<date>/observations_raw.csv` (+ gzipped HTML cache, git-ignored) | https://cenudepo.lv (category + product pages, ≥ 3 s between requests) | 2026-10-06 | n/a (snapshot) | © Cenu Depo, all rights reserved; terms do not address reuse | CSV yes |

CSP notes: prices are collected in about 2,000 outlets in Riga and 9 other towns and weighted by population. Each item's average is the arithmetic mean of collected prices. Sale prices offered to all consumers are included (CSP CPI metadata, stat.gov.lv/en/metadata/2421). Product codes were renumbered in February 2026, so match items **by name**.

## Known issues (Cenu Depo snapshot 2026-10-06)
- Each product page lists per-shop prices; single-shop products show only a "hero price" block (parsed since v2 of the parser). "ar karti" rows are card-only prices (`price_type = loyalty`) and are excluded from central prices.
- Cross-check against CSP 12-month means: Cenu Depo median is about 10 % lower (it includes discount and wholesale-type shops such as Promo, Gemoss, Velto). Kept as is; to be used as a scenario in sensitivity analysis (PLAN D.1).
- Not found on Cenu Depo: soy drink, chicken liver, sunflower/pumpkin/flax seeds, mass gainer, maltodextrin.

