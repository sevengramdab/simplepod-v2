# PyPI Trusted Publishing Setup

## What You Need to Do (One-Time Setup)

Trusted Publishing lets GitHub Actions push to PyPI **without API tokens**.
It's like a smart breaker that only trips when the right electrician
(with the right badge) flips the switch.

---

### Step 1: Create the PyPI Project

1. Go to https://pypi.org/manage/account/publishing/
2. Click **"Add a new pending publisher"**
3. Fill in:
   - **PyPI Project Name**: `simplepod-surgical-strike-swarm`
   - **Owner**: `sevengramdab`
   - **Repository name**: `simplepod-v2`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
4. Click **"Add"**

---

### Step 2: Verify It Works

The tag `v2.6.0` was already pushed. The release workflow will:

1. Generate a changelog from git history
2. Create a GitHub Release at https://github.com/sevengramdab/simplepod-v2/releases
3. Build the Python wheel + sdist
4. Publish to PyPI automatically

**Check the run:** https://github.com/sevengramdab/simplepod-v2/actions/workflows/release.yml

---

### Step 3: Install from PyPI (after publish)

```bash
pip install simplepod-surgical-strike-swarm
```

---

### Step 4: Publish npm Package (optional)

```bash
cd interfaces/web_ui/frontend
npm run build
npm login
npm publish --access public
```

---

### Troubleshooting

| Issue | Fix |
|-------|-----|
| "No module named 'build'" | `pip install build` |
| "Trusted publishing failure" | Verify the PyPI pending publisher matches exactly: owner=`sevengramdab`, repo=`simplepod-v2`, workflow=`release.yml`, environment=`pypi` |
| "Package name taken" | PyPI names are global. If `simplepod-surgical-strike-swarm` is taken, change `name` in `pyproject.toml` |
