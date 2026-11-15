# Free Video & Audio Demo Recording Guide (Windows 10 & Chrome)

A concise, step-by-step guide on how to record your complete project demo video with crystal-clear screen and voice recording for **100% free**, with **no watermarks** and **no time limits**.

---

## Method 1: Windows 10 Built-In Recorder (Zero Downloads)

Windows 10 includes a built-in hardware-accelerated recorder called **Xbox Game Bar**.

### Baby Steps:
1. **Open Google Chrome**: Navigate to your running application at [http://127.0.0.1:8000/](http://127.0.0.1:8000/).
2. **Open the Game Bar Overlay**: Press **`Win + G`** on your keyboard.
3. **Enable Your Microphone**:
   - Locate the **Capture** window (top-left).
   - Click the **Microphone icon** so it is unmuted (shortcut: **`Win + Alt + M`**).
4. **Start Recording**:
   - Click the round **Record dot** (or press **`Win + Alt + R`**).
   - A small recording timer will appear in the top-right corner showing elapsed time and an active mic icon.
5. **Present Your Project**:
   - Follow the sequenced steps in [`QUICK_DEMO_GUIDE.md`](./QUICK_DEMO_GUIDE.md).
   - Explain your project architecture, endpoints, CRUD operations, and business rules out loud.
6. **Stop Recording**:
   - Click the blue square **Stop** button on the floating timer bar (or press **`Win + Alt + R`**).
7. **Locate Your Video File**:
   - Press **`Win + G`** → click **"See my captures"**, or open Windows File Explorer to:
     ```
     This PC > Videos > Captures
     ```
   - Your video is saved as a standard, high-definition `.mp4` ready for submission or upload.

> **Note**: Game Bar records the active application window (Chrome). If you need to show your terminal window running `pytest -v`, you can either record that terminal window as a second clip or use Method 2 below to capture your entire desktop.

---

## Method 2: Screenity Chrome Extension (Best for Full Desktop & Terminal)

If you want to seamlessly switch between **Google Chrome** (frontend/Swagger) and **VS Code / PowerShell Terminal** (running unit tests and uvicorn) in a single continuous recording without cuts.

### Baby Steps:
1. **Install the Free Extension**:
   - Open Google Chrome and install **Screenity** from the [Chrome Web Store](https://chromewebstore.google.com/detail/screenity-screen-recorder/kbbdabhdfmpimajofggipgpnfnnadack).
   - *Screenity is 100% free, open-source, has zero watermarks, and imposes no video duration caps.*
2. **Pin the Extension**:
   - Click Chrome's puzzle piece icon (Extensions) in the top-right corner.
   - Click the pin icon next to **Screenity**.
3. **Configure Settings**:
   - Click the red Screenity icon in Chrome.
   - Select **"Entire Screen"**.
   - Ensure the **Microphone** dropdown is set to your active microphone and toggled **ON**.
   - (Optional) Toggle camera if you wish to include a picture-in-picture webcam bubble of yourself.
4. **Start Recording**:
   - Click **"Start Recording"** → Choose your main display → Click **"Share"**.
   - A 3-second countdown will display.
5. **Conduct the Walkthrough**:
   - Showcase your application in Chrome at `http://127.0.0.1:8000/`.
   - Switch to your terminal to demonstrate `python -m pytest tests/ -v`.
   - Switch to `/docs` to show Swagger OpenAPI schemas.
6. **Finish & Export**:
   - Click the red **Stop button** on the floating Screenity control bar.
   - In the export screen, click **Download** to save an `.mp4` or `.webm` file directly to your `Downloads` folder.

---

## Method 3: Windows Snipping Tool (Built-In Alternative)

If you have the updated Windows Snipping Tool installed:

1. Press **`Win + Shift + S`** or search for **Snipping Tool** in the Windows Start menu.
2. Click the **Video camera icon** at the top.
3. Click **New** and drag a rectangle over your entire screen.
4. Toggle the **Microphone icon** ON in the top toolbar.
5. Click **Start** to record, and click the red square to stop.
6. Click **Save** to export the `.mp4` file.

---

## Video Recording Best Practices for Full Marks

1. **Audio Test**: Record a 10-second test clip first and play it back to ensure your voice is loud and clear before recording the full run.
2. **Follow the Sequence**: Keep [`QUICK_DEMO_GUIDE.md`](./QUICK_DEMO_GUIDE.md) open on a side window or phone to smoothly hit all 18 key grading criteria.
3. **Explain "Why" & "How"**:
   - Explain how `app/db.py`, `models.py`, `schemas.py`, `services.py`, and `main.py` separate concerns.
   - Highlight the business logic blocking overbooking and duplicate registrations with `409 Conflict`.
   - Show Swagger `/docs` and the live modern UI.
4. **Upload Options**: Once recorded, upload your video to **Google Drive**, **YouTube (Unlisted)**, or **Loom**, and paste the public link in your submission document.
