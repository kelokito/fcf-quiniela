## 🏃‍♂️ Build & Run

```bash
# Build image
docker build -t fcf-app .

# Run container (with local volume to keep data)
docker run -p 8501:8501 -v "$(pwd):/app" fcf-app
```

in order to update the results of the matchday:
docker run -it --rm -v "$(pwd)/data:/app/data" fcf-app python /app/src/scraper.py

Then open in your browser or mobile:
👉 **[http://localhost:8501](http://localhost:8501)**


