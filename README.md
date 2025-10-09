
## 🏃‍♂️ Build & Run

```bash
# Build the Docker image
docker build -t fcf-app .

# Run the container (with local volume to persist data)
docker run --env-file .env -p 8501:8501 -v "$(pwd):/app" fcf-app
```

> This will start the Streamlit app and map port 8501 to your host machine. Data changes will persist because of the mounted volume.

---

## 🔄 Update Matchday Results

```bash
# Run the scraper inside the container to fetch new match data
docker run --env-file .env -it --rm -v "$(pwd)/data:/app/data" fcf-app python /app/src/main.py
```

> `--rm` ensures the container is removed after running. `-it` allows interactive output from the scraper.

---


## 🌐 Access the App

Open your browser or mobile device and go to:

👉 [http://localhost:8501](http://localhost:8501)

---

Optional: If you want **to combine scraping and running the app** in one container, you could create a small shell script like:

```bash
#!/bin/bash
python /app/src/scraper.py
streamlit run /app/src/app.py
```

And then run the container normally.

