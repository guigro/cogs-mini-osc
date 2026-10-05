# Quickstart: validation de Mini-OSC bureau

Guide de vérification de bout en bout. Détails des options : [contracts/launcher.md](contracts/launcher.md). Emplacements des fichiers : [data-model.md](data-model.md).

## 1. Mode script sans régression (US6)

```bash
source venv/bin/activate
pip install -r requirements.txt
./Start_OSC_Webapp.command
```

Attendu : le `config.json` du dossier est chargé, l'interface s'ouvre dans le navigateur, le bouton Restart relance l'application.

## 2. Lanceur bureau depuis les sources (US1 à US4)

```bash
pip install -r requirements-desktop.txt
MINI_OSC_DATA_DIR=/tmp/mini-osc-test python desktop.py
```

Attendu :
- Une fenêtre `Mini-OSC` s'ouvre sur l'interface habituelle.
- `/tmp/mini-osc-test/config.json` est créé à partir de la config par défaut.
- Ajouter une connexion HTTP vers OSC, quitter, relancer : la connexion est toujours là.
- Relancer `desktop.py` pendant qu'il tourne : pas de seconde fenêtre, la première revient au premier plan.
- Cliquer sur Restart : la fenêtre se ferme puis revient en moins de 10 s.
- Mettre une virgule en trop dans `config.json` et relancer : page d'erreur lisible, fichier non modifié.

## 3. Tests automatiques

```bash
pytest tests/
```

## 4. Exécutable empaqueté en local (Mac)

```bash
packaging/build_macos.sh
./dist/Mini-OSC.app/Contents/MacOS/Mini-OSC --smoke-test; echo $?   # attendu : 0
open dist/Mini-OSC-*.dmg
```

Couper le Wi-Fi et lancer l'application : styles et icônes s'affichent.

## 5. CI et release (US5)

```bash
git tag v2.0.0-rc1 && git push origin v2.0.0-rc1
gh run watch
gh release view v2.0.0-rc1
```

Attendu : quatre jobs verts, smoke test compris, puis une release avec quatre fichiers.

## 6. Windows et Linux x86_64

Télécharger le fichier depuis la release, le lancer, accepter SmartScreen ou le pare-feu, puis refaire les vérifications de la section 2.
