services:
  - type: web
    name: pdf-to-word-converter
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:10000
    envVars:
      - key: PYTHON_VERSION
        value: 3.10
    autoDeploy: true
