# Get Your Album Scanner APK — Step by Step

This folder contains everything needed. GitHub will build the APK for
free in about 20 minutes. You just need a free GitHub account.

---

## Step 1 — Create a free GitHub account

Go to https://github.com and sign up (free).

---

## Step 2 — Create a new repository

1. Click the **+** button (top right) → **New repository**
2. Name it: `album-scanner`
3. Set it to **Public**
4. Click **Create repository**

---

## Step 3 — Upload the files

On the new repository page, click **uploading an existing file** (or drag and drop).

Upload ALL of these files maintaining the folder structure:
```
main.py
buildozer.spec
.github/
  workflows/
    build.yml
```

**Important:** The `.github/workflows/build.yml` file must be in that exact
folder path. GitHub's file uploader lets you type the path — just type
`.github/workflows/build.yml` as the filename when uploading.

Click **Commit changes**.

---

## Step 4 — Watch the build

1. Click the **Actions** tab at the top of your repository
2. You'll see **Build Album Scanner APK** running (yellow circle = in progress)
3. Wait about **20–30 minutes** for first build (downloads Android SDK)
4. Green checkmark = success ✅

---

## Step 5 — Download the APK

1. Click the completed workflow run
2. Scroll down to **Artifacts**
3. Click **album-scanner-apk** to download a zip
4. Unzip it — inside is `albumscanner-1.0.0-arm64-v8a-debug.apk`

---

## Step 6 — Install on your Android tablet

1. **Transfer the APK** to your tablet:
   - Email it to yourself, or
   - Upload to Google Drive and open on tablet, or
   - Copy via USB cable

2. **Enable installation from unknown sources:**
   - Settings → Apps → Special app access → Install unknown apps
   - Find your file manager or Chrome → toggle ON

3. **Open the APK file** on your tablet and tap **Install**

4. Open **Album Scanner** from your app drawer 🎉

---

## Using the app

1. Enter your **Anthropic API key** — get it free at https://console.anthropic.com
2. Tap **Save Key**
3. Tap **Select Video** → find your video in Downloads or Movies
4. Tap **Scan for Album Covers**
5. Wait ~30 seconds while Claude scans the frames
6. Tap **Download CSV** to save results to Downloads

---

## Troubleshooting

**Build failed (red X in Actions)**
→ Click the run → click the job → scroll to the red step to see the error
→ Common fix: the `.github/workflows/build.yml` file is in the wrong folder

**"App not installed" on tablet**
→ Make sure "Install unknown apps" is enabled for the app you used to open the APK

**"Cannot open video"**
→ Place the video in your tablet's Downloads or Movies folder

**API key error**
→ Copy the full key from console.anthropic.com — starts with `sk-ant-`
