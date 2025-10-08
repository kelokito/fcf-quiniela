
## 🏃‍♂️ Build & Run

```bash
# Build the Docker image
docker build -t fcf-app .

# Run the container (with local volume to persist data)
docker run -p 8501:8501 -v "$(pwd):/app" fcf-app
```

> This will start the Streamlit app and map port 8501 to your host machine. Data changes will persist because of the mounted volume.

---

## 🔄 Update Matchday Results

```bash
# Run the scraper inside the container to fetch new match data
docker run -it --rm -v "$(pwd)/data:/app/data" fcf-app python /app/src/scraper.py
```

> `--rm` ensures the container is removed after running. `-it` allows interactive output from the scraper.

---

## ❌ Drop All Predictions / Reset DB

```bash
# Run the script to drop all predictions
docker run -it --rm -v "$(pwd)/data:/app/data" -w /app/src fcf-app python -m drop_db
```

> This will remove all stored predictions from the database.

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

