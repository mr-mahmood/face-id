import requests
from datetime import datetime

# -----------------------------
# Send request to fetch all active gates
# -----------------------------
def fetch_gates_from_backend():
    API_URL = "http://127.0.0.1:8000/api/access/internal/gate/"
    headers = {"Authorization": "Bearer sUpErsecreTcvtoken123@#fg5"}
    response = requests.get(API_URL, headers=headers).json()
    
    gates = []
    
    if response["success"] == True and response["data"] != []:
        gates = response["data"]["gates"]

    for idx, gate in enumerate(gates):
        gate["gate_idx"] = idx
    
    return gates
# -----------------------------
# Divide the list of gates into fixed-size chunks for parallel processing
# -----------------------------
def split_gates(gates, chunk_size=5):
    return [gates[i:i+chunk_size] for i in range(0, len(gates), chunk_size)]
        
    
def log(label, message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"\n{now} | {label:<30} | {message}", end='')