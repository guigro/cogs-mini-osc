#!/bin/bash

# ================================
# OSC HTTP WebApp - Lanceur Mac
# ================================

echo "🚀 Démarrage de l'OSC HTTP WebApp..."
echo "=================================="

# Se placer dans le répertoire du script
cd "$(dirname "$0")" || exit 1

# Vérifier que le répertoire venv existe
if [ ! -d "venv" ]; then
    echo "❌ Erreur: Le répertoire 'venv' n'existe pas."
    echo "Veuillez créer l'environnement virtuel avec:"
    echo "python -m venv venv"
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

echo "📁 Répertoire de travail: $(pwd)"

# Activation de l'environnement virtuel
echo "🔧 Activation de l'environnement virtuel Python..."
source venv/bin/activate

if [ $? -eq 0 ]; then
    echo "✅ Environnement virtuel activé avec succès"
else
    echo "❌ Erreur lors de l'activation de l'environnement virtuel"
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

# Vérification et installation des dépendances si nécessaire
if [ -f "requirements.txt" ]; then
    echo "📦 Vérification des dépendances Python..."
    pip install -r requirements.txt --quiet
    if [ $? -eq 0 ]; then
        echo "✅ Dépendances à jour"
    else
        echo "⚠️  Avertissement: Problème avec les dépendances"
    fi
fi

# Vérification que le fichier principal existe
if [ ! -f "mini_osc.py" ]; then
    echo "❌ Erreur: Le fichier 'mini_osc.py' n'existe pas."
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

# Vérification du fichier de configuration
if [ ! -f "config.json" ]; then
    echo "❌ Erreur: Le fichier 'config.json' n'existe pas."
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

# Lire la configuration Flask
FLASK_IP=$(python -c "import json; cfg=json.load(open('config.json')); print(cfg['flask_server']['ip'])" 2>/dev/null)
FLASK_PORT=$(python -c "import json; cfg=json.load(open('config.json')); print(cfg['flask_server']['port'])" 2>/dev/null)

if [ -z "$FLASK_IP" ] || [ -z "$FLASK_PORT" ]; then
    echo "⚠️  Configuration par défaut utilisée (127.0.0.1:5000)"
    FLASK_IP="127.0.0.1"
    FLASK_PORT="5000"
fi

echo "=================================="
echo "🌐 Serveur Flask: http://$FLASK_IP:$FLASK_PORT"
echo "🎯 OSC Server: Voir config.json pour les détails"
echo "=================================="

# Ouvrir le navigateur après un petit délai
sleep 3 && open "http://$FLASK_IP:$FLASK_PORT" &

echo "🎉 Lancement de l'application..."
echo "📱 Le navigateur va s'ouvrir automatiquement"
echo ""
echo "💡 Conseils:"
echo "   • Pour arrêter: Appuyez sur Ctrl+C"
echo "   • Les logs s'affichent ci-dessous"
echo "   • La fenêtre doit rester ouverte"
echo ""
echo "=================================="

# Lancement de l'application
python mini_osc.py

# Si l'application se ferme
echo ""
echo "🛑 Application fermée"
echo "Appuyez sur Entrée pour fermer cette fenêtre..."
read