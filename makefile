run-api: 
	uvicorn api.app:app --port 8000 --reload

run-extension:
	chrome --load-extension=extension --remote-debugging-port=9222

run-streamlit:
	streamlit run app/app.py --server.port 8501