FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=8000
RUN useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser app.py network.py robots.py sitemap.py limits.py ./
COPY --chown=appuser:appuser static/ ./static/
USER appuser
EXPOSE 8000
CMD ["python", "app.py"]
