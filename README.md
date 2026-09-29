# Little List

A to-do app using **React**, **Python / FastAPI**, and **SQLite**.

## Accounts and private lists

Create an account on the sign-in page using a username and a password of at least 12 characters. Each account has its own tasks and notes. Use Sign out on shared computers. Sessions expire after seven days. Password recovery is not yet available; save your password securely.

## Open the app

Once setup is complete, double-click `start.bat` in this folder. Keep the window open, then visit **http://127.0.0.1:8000** in your browser. Press Ctrl+C in that window to stop the app.

- Type a task and press Enter or click **Add task**.
- Click its checkbox to complete it; click again to undo completion.
- Drag the dotted handle to reorder tasks. The up/down buttons also work with a keyboard or on a phone-sized screen.
- Click **Edit task** to rename a task, set or clear its due date, and choose low, medium, or high priority. Click **Save changes** to save. Past due dates are highlighted for unfinished tasks.
- Search task names and notes, or filter by pending/completed/overdue status and priority. Clear filters before reordering or using numbered voice commands. Task numbers always refer to the full list.
- Click × to move a task to **Deleted tasks**. Click **Undo** immediately or **Restore** in Deleted tasks later, even after a reload. Notes, completion, dates, and priorities are preserved.
- Tasks save automatically, including completion and order.
- Expand **Add a note** under any task to write details (up to 5,000 characters), then click **Save note**. Reopen **View / edit note** to change it. Clear the text and save to remove the note. Notes stay attached when you complete, reorder, delete, or restore tasks and are saved in SQLite.

## Voice features

- **Speak a task:** click, allow microphone access, say your task, and pause. Review the words in the task box, then click Add task.
- **Voice command:** say “add buy milk”, “complete the first task”, “uncheck task one”, “move task two up”, “move task one to position three”, or “read my tasks”. Commands act on the numbered list, including completed tasks. Adding, completion, and order save to SQLite as usual.
- **Read my tasks:** reads each task and whether it is complete. Use Stop reading to cancel.
- **Cancel listening:** discards the current phrase without applying a command. Each microphone session stops after one phrase or 20 seconds; there is no always-on listening.
- Expand **Commands & microphone help** for examples and a typed command fallback.

Speech is set to English. Browser support varies: if input is unavailable in the embedded browser, open http://127.0.0.1:8000 in Chrome and allow its microphone prompt. An internet connection may be required. The browser may send audio to its speech recognition provider; the app itself does not save recordings. Readouts use your browser's speech synthesis. No API key is needed. Actual recognition accuracy depends on your microphone and browser's service.

Run `node --test src/voiceCommands.test.js` to test command interpretation without using a microphone.

## Where your data lives

Your tasks are stored in `backend/tasks.sqlite3`. Closing the browser or stopping the server does not erase them. To make a backup, stop the app and copy that file somewhere safe. Local accounts and data stay on this computer. Public hosting uses a separate Turso libSQL database; see DEPLOYMENT.md. App restarts do not erase cloud data. Do not expose the local development server directly to the internet.

Tasks from before private accounts were added are preserved but hidden. After creating your account, run `python -m backend.assign_legacy --username YOUR_USERNAME` using the virtual environment to assign local legacy tasks. This is never automatic during signup.

## How it works

`src/main.jsx` is the React interface; `src/style.css` controls its appearance. React sends requests to `backend/main.py`, the FastAPI server, which reads and writes local SQLite or remote Turso libSQL through `backend/storage.py`. Credentials stay on the backend. The production frontend is built into `dist/`, and FastAPI serves it alongside the API. API documentation is available at http://127.0.0.1:8000/docs while running.

## First-time setup on another computer

Install Python 3.10 or newer and Node.js 22 or newer. In a terminal in this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm install
npm run build
.\start.bat
```

This workspace uses pnpm and includes `pnpm-lock.yaml` for reproducible frontend installations. If pnpm is installed, use `pnpm install --frozen-lockfile` and `pnpm run build` instead of npm.

## Make changes

For a live-updating frontend, run the backend in one terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

In another terminal, run `npm run dev` (or `pnpm run dev`) and open the address Vite prints. It forwards API requests to port 8000. After editing the frontend, run `npm run build` and restart the backend to update the normal app.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest backend.test_api -v
```

Tests use a separate temporary database and verify adding, validation, completion, reordering, persistence across app restarts, and deletion without touching your tasks.
