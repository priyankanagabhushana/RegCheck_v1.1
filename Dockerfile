FROM python:3.12-slim

WORKDIR /app

# Install system deps for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY schemas/ schemas/
COPY parsers/ parsers/
COPY compilers/ compilers/
COPY graph/ graph/
COPY agents/ agents/
COPY reports/ reports/
COPY demos/ demos/
COPY evaluation/ evaluation/
COPY tests/ tests/
COPY data/output/ data/output/
COPY data/study6_compare_trials_dataset/ data/study6_compare_trials_dataset/
COPY main.py .
COPY app.py .
COPY auth.py .
COPY __init__.py .

RUN pip install --no-cache-dir \
    pydantic>=2.0 \
    networkx>=3.0 \
    langgraph>=0.2.0 \
    langchain-core>=0.3.0 \
    rich>=13.0 \
    typer>=0.9.0 \
    streamlit>=1.30.0 \
    plotly>=5.0.0 \
    litellm>=1.0.0 \
    instructor>=1.0.0 \
    PyMuPDF>=1.24.0 \
    docling>=2.0.0

EXPOSE 8080

HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", \
            "--server.port=8080", \
            "--server.address=0.0.0.0", \
            "--server.headless=true", \
            "--browser.gatherUsageStats=false"]
