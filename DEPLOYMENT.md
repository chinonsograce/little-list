# Free public deployment

The Dockerfile builds React and serves it with FastAPI at one public URL. SQLite remains the database. The Render blueprint explicitly uses the Free plan, with no paid disk or database.

## Limits of this assignment demo

Everyone shares the same task list and can edit it. Do not enter personal information. Render Free uses temporary storage: task changes can disappear when the app sleeps, restarts, or redeploys. The first visit after inactivity can take longer to load. Your local SQLite database is excluded from GitHub and from the deployment image.

## GitHub

Create an empty repository named `little-list` in your GitHub account. Upload the project source, including Dockerfile and render.yaml. Do not upload .venv, node_modules, database files, or secrets. Use a public repository if your assignment requires publicly accessible code.

## Render

1. Sign in at https://dashboard.render.com/ and connect your GitHub account.
2. Choose New > Blueprint and select the repository containing this project.
3. Check that the service uses **Free**. Do not upgrade or add a paid disk.
4. Deploy and wait for the service to become Live.
5. Open the generated HTTPS onrender.com address and test adding a task, notes, editing, and restore. Use /api/health to check the server and /docs for API documentation.
6. Submit the GitHub repository URL and the public app URL.

Official documentation: https://render.com/docs/free and https://render.com/docs/docker
