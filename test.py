import requests

try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    print("✓ Ollama działa!")
    print("Dostępne modele:", response.json())
except:
    print("✗ Ollama nie odpowiada - uruchom GUI")