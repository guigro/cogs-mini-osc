# Implementation Plan: Mini-OSC en logiciel de bureau autonome

**Branch**: `feature/desktop-app` | **Date**: 2026-10-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-desktop-app/spec.md`

## Summary

Empaqueter Mini-OSC en application de bureau autonome pour quatre plateformes (macOS arm64 et Intel, Windows x64, Linux x86_64). Un nouveau lanceur `desktop.py` démarre le moteur existant de `mini_osc.py` dans un thread, puis ouvre une fenêtre native pywebview sur l'interface Flask actuelle. PyInstaller produit les exécutables, et GitHub Actions les construit, les teste (smoke test) et les publie à chaque tag. Les modifications de `mini_osc.py` se limitent au démarrage, aux chemins de fichiers, aux erreurs de configuration et au point d'accroche du Restart. Le routage et l'interface ne changent pas, hormis le chargement local de Bulma et Font Awesome.

## Technical Context

**Language/Version**: Python 3.12 pour les builds (le mode script reste compatible avec le Python actuel de l'utilisateur)

**Primary Dependencies**: existantes (Flask, Flask-Cors, requests, python-osc) ; bureau : pywebview 5.x (pyobjc sur macOS, pythonnet sur Windows, PyGObject `<3.51` sur Linux), PyInstaller 6.x

**Storage**: fichiers JSON (`config.json`) et logs texte rotatifs, dans le dossier de données (voir [data-model.md](data-model.md))

**Testing**: pytest (fonctions du lanceur) + option `--smoke-test` de l'exécutable lancée en CI sur les quatre plateformes + vérification manuelle de la fenêtre

**Target Platform**: macOS 12+ (arm64, x86_64), Windows 10/11 x64 (WebView2), Linux x86_64 avec glibc 2.35+ et WebKitGTK 4.1 (Ubuntu 22.04+, Debian 12+). Raspberry Pi hors périmètre pour l'instant

**Project Type**: application de bureau (enveloppe autour d'un serveur local existant)

**Performance Goals**: interface utilisable moins de 10 s après le double-clic (SC-002), Restart en moins de 10 s

**Constraints**: hors ligne ; applications non signées ; fichier unique par plateforme ; aucune modification du routage ni de l'interface ; mode script inchangé

**Scale/Scope**: un fichier source modifié (`mini_osc.py`, environ 40 lignes touchées), un nouveau lanceur (environ 250 lignes), 2 fichiers vendor, 1 config par défaut, 1 spec PyInstaller, 1 workflow CI, tests, README

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` est encore le modèle vierge : aucun principe de projet n'est ratifié, donc aucune barrière formelle. On applique à la place les contraintes posées par l'utilisateur :

| Contrainte | Respect dans ce plan |
|---|---|
| Ne rien changer au fonctionnement ni à l'UI | Le moteur de routage n'est pas touché ; `index.html` ne change que par 2 URL de ressources |
| Mode script toujours fonctionnel | Dossier de données = dossier du script, Restart par code 42 conservé tel quel |
| Pas de typographie à tiret long | Respecté dans le code, les messages et la documentation |

Revérification après la phase 1 : conforme, rien à justifier.

## Project Structure

### Documentation (this feature)

```text
specs/001-desktop-app/
├── plan.md              # Ce fichier
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── launcher.md      # Contrat du lanceur (options, chemins, codes de sortie, verrou)
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
mini_osc.py                  # Modifié : DATA_DIR, ConfigError, start_servers(), restart_callback
desktop.py                   # Nouveau : lanceur bureau (dossier de données, verrou, fenêtre, erreurs, smoke test)
index.html                   # Modifié : 2 balises pointent sur vendor/
vendor/
├── bulma.min.css            # Nouveau : Bulma 0.9.3
└── fontawesome-all.min.js   # Nouveau : Font Awesome 5.15.4 (SVG+JS)
config.default.json          # Nouveau : config du premier lancement
requirements.txt             # Inchangé (mode script)
requirements-desktop.txt     # Nouveau : pywebview, pyinstaller (+ marqueurs par plateforme)
packaging/
├── mini_osc.spec            # Nouveau : spec PyInstaller commune aux plateformes
├── build_macos.sh           # Nouveau : .app vers .dmg
├── build_linux.sh           # Nouveau : onedir vers AppDir vers AppImage
├── mini-osc.desktop         # Nouveau : entrée de bureau Linux
└── icons/                   # Nouveau : icône (.icns, .ico, .png)
.github/workflows/build.yml  # Nouveau : matrice 4 plateformes, smoke test, release
tests/
├── test_data_dir.py         # Nouveau
├── test_config_bootstrap.py # Nouveau
├── test_single_instance.py  # Nouveau
└── test_window_url.py       # Nouveau
README.md                    # Modifié : téléchargement, premier lancement, emplacement de la config
```

**Structure Decision**: on garde le fichier unique `mini_osc.py` comme moteur (convention du projet) et on ajoute à côté un lanceur `desktop.py` séparé, qui en est le seul consommateur en mode bureau. Tout ce qui sert uniquement au build va dans `packaging/` et `.github/`.

### Modifications de `mini_osc.py` (détail)

1. `DATA_DIR` (par défaut `current_dir`) et `CONFIG_FILE = os.path.join(DATA_DIR, "config.json")`, plus une fonction `set_data_dir(path)` appelée par le lanceur avant tout chargement.
2. `setup_file_logging` écrit dans `os.path.join(DATA_DIR, "logs")` au lieu de `current_dir/logs`.
3. `load_config` lève `ConfigError(message)` au lieu de `print` + `sys.exit(1)`.
4. Le contenu du bloc `if __name__ == "__main__":` passe dans une fonction `start_servers(run_flask=True)`. Le bloc `__main__` l'appelle, attrape `ConfigError`, l'affiche et sort avec le code 1 : même comportement qu'aujourd'hui.
5. `restart_callback = None` ; la route `/restart` l'appelle s'il est défini, sinon garde `os._exit(42)`.
6. Au démarrage, un log indique le chemin du fichier de configuration utilisé (FR-017).

## Phasage d'implémentation conseillé

1. Modifications de `mini_osc.py` et ressources vendor (mode script vérifié sans régression).
2. `desktop.py` et les tests pytest.
3. Spec PyInstaller et scripts de build, validés en local sur Mac.
4. Build Linux en CI tôt (risque principal, R4 : la fenêtre GTK empaquetée).
5. Workflow CI sur les quatre plateformes, smoke test, release.
6. README et vérifications manuelles (quickstart).

## Complexity Tracking

Aucune violation à justifier.
