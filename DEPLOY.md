# Sharing the app with friends (Streamlit Community Cloud, private)

The app runs from a **private** GitHub repository on Streamlit Community Cloud (free), and only people you invite by
email can open it. Everything the app needs is already committed: `data/processed/foods_master.csv`, `config/`,
`data/foods/`, `data/prices/eurostat_pli_food.csv`. The 97 MB USDA download is not needed.

> The prices include Cenu Depo data that is for **personal use only**, so keep both the repository and the app private
> (invite-only) and don't make either public.

## 1. Push the code to a private GitHub repository (once)
1. On github.com: **New repository**, name e.g. `nutrition`, choose **Private**, and don't add a README or .gitignore.
2. In the project folder (normal terminal, or `host-spawn` inside VS Code):
   ```sh
   git remote add origin git@github.com:<your-user>/nutrition.git    # or the https:// URL GitHub shows
   git push -u origin main
   ```
   The push includes `data/raw/` (Frida, CSP, Cenu Depo snapshot, EFSA PDFs, Eurostat), about 22 MB.
   `.gitignore` excludes the USDA files, literature PDFs, `.work/` and `exports/`.

## 2. Deploy (once)
1. Go to <https://share.streamlit.io>, sign in with GitHub, and allow access to the private repository.
2. **Create app** → *Deploy from GitHub*:
   - Repository: `<your-user>/nutrition`, branch `main`
   - Main file path: **`app/app.py`** (its dependencies are in `app/requirements.txt`)
   - **Advanced settings**:
     - Python version: the newest one offered. The app is tested on 3.14; 3.13 should also work.
     - **Secrets**: paste
       ```toml
       NUTRITION_DEFAULT_PROFILE = "general_adult"
       ```
       This makes friends start from a neutral adult profile instead of yours (top-level secrets become environment
       variables). Leave it out to keep `owner` as the default.
3. Deploy. The first build takes a few minutes while the packages install.

## 3. Invite friends
App page → **Share** (top right) → keep it **private / only specific people**, then add your friends' email
addresses. Each friend gets an invitation and signs in with that email, or a Google/GitHub account using the same
address. Community Cloud's limits on private apps can change, so if it refuses, check the current plan limits in
your workspace settings.

## 4. Who uses it (traffic)
App page or workspace → ⋮ → **Analytics** shows the total number of viewers and the most recent viewers (for a
private app these are invited accounts). Only invited people can open a private app; forwarding the link alone does
not give access.

## 5. Updating
`git push` to `main`, and the app redeploys automatically within a minute or two. After changing data or config,
rebuild first (`sh run_all.sh`) so the committed `foods_master.csv` is current.

## 6. Message for friends (copy and adapt)
> Hi! Here's my nutrition calculator: <app link>.
> 1. Pick your country (top right), Denmark or the Netherlands. Prices are Latvian shop prices scaled by
>    official EU food price levels, so treat them as approximate.
> 2. In **My profile** (the start page), enter your sex, age, weight, height, training and goal, then press *Save & calculate targets*.
> 3. Open **Improve what you eat → Rate & improve a meal**. Your meal (e.g. 4 eggs + 1 can of beans) gets a 0–100 score against your own
>    needs, plus an improved meal with the same calories. Weigh food *as eaten* (1 egg ≈ 51 g, 1 can of beans
>    ≈ 240 g drained).
> It's a hobby project, not medical advice.

## Running locally (unchanged)
`.venv/bin/streamlit run app/app.py --server.address localhost` (inside the VS Code Flatpak terminal, prefix
`host-spawn`). Local runs are bound to this computer by that flag; `.streamlit/config.toml` is shared with the cloud.
