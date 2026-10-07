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

## Added 2026-10-07
| Dataset | Local path | Source URL | Downloaded | SHA-256 | License | In git? |
|---|---|---|---|---|---|---|
| EFSA DRV summary report (2017) | `data/raw/efsa/efsa_drv_summary_report_2017.pdf` | https://www.efsa.europa.eu/sites/default/files/2017_09_DRVs_summary_report.pdf | 2026-10-07 | `0231c27d944b9d9ec209d9b6c8d42b9a969df6054f0e30ff7e945bb77d532c48` | © EFSA, reproduction authorised with acknowledgement | yes |
| EFSA DRV summary tables v4 (Sept 2017) | `data/raw/efsa/efsa_drv_summary_tables_2017.pdf` | https://www.efsa.europa.eu/sites/default/files/assets/DRV_Summary_tables_jan_17.pdf | 2026-10-07 | `0786be9b090eb97eb87c9f1c4388d3cde4371da528246553b4631e9bee1a59bc` | same | yes |
| EFSA overview of Tolerable Upper Intake Levels, version 11 (Aug 2025) | `data/raw/efsa/efsa_ul_summary_report.pdf` | https://www.efsa.europa.eu/sites/default/files/2024-05/ul-summary-report.pdf | 2026-10-07 | `3d723ca33ef1bb850ac29b159f7a2676ec61379d880bafebc412dde85e35224e` | same | yes |

| Eurostat prc_ppp_ind, food price level indices (PLI, EU27_2020 = 100), JSON-stat 2.0; dataset updated 2025-07-10, latest year 2024 | `data/raw/eurostat/prc_ppp_ind_food.json` | https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_ppp_ind?na_item=PLI_EU27_2020&ppp_cat=A010101&ppp_cat=A01010101&ppp_cat=A01010102&ppp_cat=A01010103&ppp_cat=A01010104&ppp_cat=A01010105&ppp_cat=A01010106&ppp_cat=A01010199 | 2026-10-07 | `3348c5b142d1196d3e5e12176aa78ce1b0cb9aba97e0022a050c337bde7a576c` | Eurostat, free re-use with acknowledgement (Commission Decision 2011/833/EU) | yes |

Eurostat notes: converted by `python -m src.prices.countries` to `data/prices/eurostat_pli_food.csv`. Country prices = Latvian price × PLI(country, category) / PLI(LV, category); see `src/prices/countries.py`.
