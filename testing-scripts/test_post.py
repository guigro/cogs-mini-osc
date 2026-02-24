#!/usr/bin/env python3
"""
Script de test pour les requêtes HTTP POST vers l'application OSC HTTP Webapp
"""

import requests
import json
import sys

# Configuration du serveur
BASE_URL = "http://127.0.0.1:5009"
SEND_OSC_ENDPOINT = "/send_osc"

def test_post_request(address, args, description=""):
    """Test une requête POST vers /send_osc"""
    url = BASE_URL + SEND_OSC_ENDPOINT
    
    payload = {
        "address": address,
        "args": args
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"\n--- {description} ---")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ ERREUR: Impossible de se connecter au serveur")
        print("   Vérifiez que l'application est démarrée sur 127.0.0.1:5009")
        return False
    except requests.exceptions.Timeout:
        print("❌ ERREUR: Timeout de la requête")
        return False
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

def test_get_request(address, args, description=""):
    """Test une requête GET vers /send_osc pour comparaison"""
    url = BASE_URL + SEND_OSC_ENDPOINT
    
    params = {"address": address}
    for i, arg in enumerate(args):
        params[f"arg{i}"] = arg
    
    print(f"\n--- {description} (GET) ---")
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

def main():
    print("🧪 Tests des requêtes HTTP POST vers l'OSC HTTP Webapp")
    print("=" * 60)
    
    # Tests POST
    tests = [
        ("/test", ["hello", "world"], "Test simple avec arguments"),
        ("/quiz1", ["start", "set1"], "Test route quiz1"),
        ("/multiball", ["game123", 5, "hard"], "Test route multiball"),
        ("/grid", [1, 50, "medium", 2], "Test route grid"),
        ("/generateur", ["activate", 100], "Test route générateur"),
    ]
    
    success_count = 0
    total_tests = len(tests)
    
    for address, args, description in tests:
        if test_post_request(address, args, f"POST - {description}"):
            success_count += 1
            print("✅ SUCCESS")
        else:
            print("❌ FAILED")
    
    print(f"\n📊 Résultats POST: {success_count}/{total_tests} tests réussis")
    
    # Test GET pour comparaison
    print(f"\n🔄 Test GET pour comparaison:")
    if test_get_request("/test", ["hello", "world"], "GET - Test simple"):
        print("✅ SUCCESS")
    else:
        print("❌ FAILED")

if __name__ == "__main__":
    main()