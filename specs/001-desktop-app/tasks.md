# Tasks: Mini-OSC en logiciel de bureau autonome

**Input**: Design documents from `specs/001-desktop-app/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/launcher.md](contracts/launcher.md), [quickstart.md](quickstart.md)

**Tests**: inclus (pytest pour les fonctions pures du lanceur, et smoke test des exécutables), comme prévu dans le plan (R13).

**Organization**: tâches groupées par user story ; chaque story peut être vérifiée séparément.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallélisable (fichiers différents, aucune dépendance sur une tâche non terminée)
- **[Story]**: user story concernée (US1 à US6)

---

## Phase 1: Setup

**Purpose**: dépendances, ressources locales, squelette de tests

- [X] T001 Ajouter `build/`, `dist/`, `*.AppImage`, `*.dmg` et `AppDir/` à `.gitignore`
- [X] T002 [P] Créer `requirements-desktop.txt` : `-r requirements.txt`, `pywebview>=5,<6`, `pyinstaller>=6,<7`, `pytest`, et `PyGObject>=3.42,<3.51 ; sys_platform == "linux"` (R4)
- [X] T003 [P] Télécharger Bulma 0.9.3 (`https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.3/css/bulma.min.css`) dans `vendor/bulma.min.css` et Font Awesome 5.15.4 (`https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/js/all.min.js`) dans `vendor/fontawesome-all.min.js` ; vérifier que les fichiers ne sont pas vides et commencent par l'en-tête de licence attendu (R8)
- [X] T004 [P] Créer `config.default.json` avec le contenu exact de [data-model.md](data-model.md) (section « Configuration par défaut »)
- [X] T005 [P] Créer `tests/__init__.py` (vide) et `tests/conftest.py`, qui ajoute la racine du dépôt à `sys.path`

---

## Phase 2: Foundational (bloquant)

**Purpose**: rendre `mini_osc.py` pilotable par un lanceur, sans changer son comportement en mode script

**⚠️ CRITICAL**: aucune user story ne commence avant la fin de cette phase

- [X] T006 Dans `mini_osc.py`, ajouter `DATA_DIR = current_dir`, `CONFIG_FILE = os.path.join(DATA_DIR, "config.json")` et `def set_data_dir(path)`, qui met à jour les globales `DATA_DIR` et `CONFIG_FILE` et crée le dossier s'il manque
- [X] T007 Dans `mini_osc.py`, `setup_file_logging` : remplacer `os.path.join(current_dir, "logs")` par `os.path.join(DATA_DIR, "logs")`
- [X] T008 Dans `mini_osc.py`, ajouter `class ConfigError(Exception)` ; dans `load_config`, remplacer chaque couple `print(...)` + `sys.exit(1)` par `raise ConfigError(<même message>)`
- [X] T009 Dans `mini_osc.py`, déplacer le corps du bloc `if __name__ == "__main__":` dans `def start_servers(run_flask=True)` (chargement, sauvegarde après migration, `expand_connections`, `setup_file_logging`, serveurs OSC/TCP/UDP, puis `app.run` si `run_flask`). Ajouter `add_log(f"Config file: {CONFIG_FILE}")` au démarrage (FR-017). Le bloc `__main__` appelle `start_servers()` dans un `try`, attrape `ConfigError`, affiche le message et sort avec `sys.exit(1)`
- [X] T010 Dans `mini_osc.py`, ajouter `restart_callback = None` ; la route `/restart` appelle `restart_callback()` (dans le thread différé existant) s'il est défini, sinon garde `os._exit(42)`
- [X] T011 Vérifier qu'il n'y a pas de régression en mode script : `python mini_osc.py` charge le `config.json` du dépôt, `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5009/` renvoie 200, et un `config.json` volontairement invalide (copie temporaire) donne le même message qu'avant et le code de sortie 1

**Checkpoint**: le moteur est pilotable, le mode script est identique

---

## Phase 3: User Story 1 - Lancer Mini-OSC d'un double-clic dans sa propre fenêtre (Priority: P1) 🎯 MVP

**Goal**: un exécutable qui démarre les serveurs et ouvre une fenêtre native sur l'interface actuelle, hors ligne ; fermer la fenêtre quitte

**Independent Test**: sur une machine sans Python, lancer l'exécutable, voir l'interface complète, router un message HTTP vers OSC ; fermer la fenêtre libère les ports

### Tests for User Story 1

- [X] T012 [P] [US1] Écrire `tests/test_window_url.py` : `window_url({"ip": "127.0.0.1", "port": 5000})` donne `http://127.0.0.1:5000/` ; `0.0.0.0` et `::` donnent `127.0.0.1` ; une IP LAN est conservée
- [X] T013 [P] [US1] Écrire `tests/test_data_dir.py` : `default_data_dir()` selon `sys.platform` simulé (`darwin`, `win32` avec `APPDATA`, `linux` avec et sans `XDG_CONFIG_HOME`), et priorité de `MINI_OSC_DATA_DIR` (data-model.md)

### Implementation for User Story 1

- [X] T014 [US1] Dans `index.html`, remplacer les deux balises CDN (lignes 8 et 9) par `<link rel="stylesheet" href="vendor/bulma.min.css">` et `<script src="vendor/fontawesome-all.min.js"></script>` ; ne rien changer d'autre (FR-005, FR-007)
- [X] T015 [US1] Créer `desktop.py` avec `default_data_dir()` (R6), `window_url(flask_cfg)` (R11), `resource_dir()` (`sys._MEIPASS` si empaqueté, sinon dossier du fichier) et l'analyse des options `--wait-lock` / `--smoke-test` ([contracts/launcher.md](contracts/launcher.md)) ; faire passer T012 et T013
- [X] T016 [US1] Dans `desktop.py`, `main()` : `mini_osc.set_data_dir(...)`, créer `config.json` depuis `config.default.json` s'il est absent, lancer `mini_osc.start_servers()` dans un thread `daemon` en capturant toute exception dans une variable partagée, attendre que le port HTTP accepte une connexion (15 s maximum), puis ouvrir `webview.create_window("Mini-OSC", url, width=1280, height=860)` et `webview.start()`
- [X] T017 [US1] Dans `desktop.py`, page d'erreur : si les serveurs échouent ou ne répondent pas dans le délai, ouvrir la fenêtre avec un HTML local (message d'erreur, chemin de `config.json`, bouton Quitter) au lieu de l'URL (FR-013, R11)
- [X] T018 [US1] Dans `desktop.py`, après le retour de `webview.start()`, appeler `os._exit(0)` (FR-006, R12)
- [X] T019 [US1] Dans `desktop.py`, `--smoke-test` : dossier de données temporaire, ports libres choisis au hasard écrits dans la config de test, serveurs sans fenêtre, `GET /` et `GET /vendor/bulma.min.css` doivent répondre 200, puis sortie avec 0 ou 1 (R13)
- [X] T020 [US1] Vérifier en local avec `MINI_OSC_DATA_DIR=/tmp/mini-osc-test python desktop.py` (quickstart section 2) : fenêtre ouverte, interface stylée Wi-Fi coupé, message HTTP vers OSC routé, ports libérés après fermeture (`lsof -i :5000` vide)
- [X] T021 [US1] Créer `packaging/mini_osc.spec` (PyInstaller) : script `desktop.py`, données `index.html`, `vendor/`, `config.default.json`, nom `Mini-OSC`, `console=False` ; `BUNDLE` (`.app`, identifiant `show.eclipsium.mini-osc`) sur macOS ; onefile sur Windows ; onedir sur Linux
- [X] T022 [P] [US1] Créer `packaging/build_macos.sh` : `pyinstaller packaging/mini_osc.spec`, smoke test du binaire dans le `.app`, puis `hdiutil create -volname Mini-OSC -srcfolder dist/Mini-OSC.app -ov -format UDZO dist/Mini-OSC-$VERSION-macos-$ARCH.dmg`
- [X] T023 [P] [US1] Créer `packaging/mini-osc.desktop` et `packaging/build_linux.sh` : `pyinstaller`, construction d'`AppDir/` (`AppRun` qui exécute `usr/bin/Mini-OSC/Mini-OSC "$@"`, fichier `.desktop`, icône), exclusion des bibliothèques GTK et WebKit collectées par le hook `gi` si elles empêchent l'usage de celles du système (R4), smoke test, puis `appimagetool` (runtime statique, R5) vers `dist/Mini-OSC-$VERSION-linux-$ARCH.AppImage`
- [X] T024 [US1] Construire en local sur Mac avec `packaging/build_macos.sh`, vérifier le smoke test (code 0), ouvrir le `.dmg`, lancer l'application et refaire les vérifications de T020
- [ ] T025 [US1] **Build Linux tôt (risque R4)** : créer `.github/workflows/build.yml` avec, pour l'instant, le seul job `linux-x86_64` (`ubuntu-22.04`, Python 3.12, `apt install libgirepository1.0-dev libcairo2-dev gir1.2-webkit2-4.1 libwebkit2gtk-4.1-0`, `pip install -r requirements-desktop.txt`, `packaging/build_linux.sh` smoke test compris, envoi de l'AppImage en artefact), déclenché par `workflow_dispatch` ; le lancer avec `gh workflow run` et corriger jusqu'au vert
- [ ] T026 [US1] Vérifier que la fenêtre GTK de l'AppImage s'ouvre vraiment : dans le job CI, lancer l'AppImage sous `xvfb-run` pendant 10 s et vérifier qu'il ne plante pas au chargement de WebKitGTK (code de sortie et journal) ; en cas d'échec, corriger `packaging/build_linux.sh` ou `packaging/mini_osc.spec`. Le test sur une vraie machine Linux reste en T049

**Checkpoint**: MVP utilisable sur Mac (build local), AppImage Linux produite et testée en CI

---

## Phase 4: User Story 2 - Configuration et logs conservés (Priority: P1)

**Goal**: config et logs dans le dossier utilisateur, config par défaut au premier lancement, config invalide jamais écrasée, emplacement visible

**Independent Test**: ajouter une connexion, quitter, relancer : elle est là. Remplacer l'application : elle est toujours là. Config invalide : page d'erreur, fichier intact

### Tests for User Story 2

- [ ] T027 [P] [US2] Écrire `tests/test_config_bootstrap.py` : `ensure_config(data_dir, default_path)` copie la config par défaut si elle est absente, ne touche pas une config existante (comparer le contenu octet par octet), et ne touche pas une config invalide ; `mini_osc.load_config` lève `ConfigError` sur un JSON invalide et sur une section manquante ; l'ancien format `targets` + `routes` est migré en `connections`

### Implementation for User Story 2

- [ ] T028 [US2] Extraire dans `desktop.py` la création de la config du premier lancement en `ensure_config(data_dir, default_path)` ; faire passer T027
- [ ] T029 [US2] Dans `desktop.py`, quand l'exception capturée est une `ConfigError`, la page d'erreur indique « Configuration illisible », le message, et le chemin de `config.json` à corriger ; vérifier que le fichier n'est pas modifié (comparer son horodatage avant et après)
- [ ] T030 [US2] Vérifier que les logs fichiers vont dans `<DataDir>/logs/` quand `file_logging.enabled` est vrai, en mode bureau (`MINI_OSC_DATA_DIR`) comme en mode script (dossier du script)
- [ ] T031 [US2] Vérification manuelle : 10 cycles quitter/relancer sans perte, puis remplacement du `.app` par un nouveau build sans perte (SC-005)

**Checkpoint**: US1 et US2 forment une application exploitable en salle

---

## Phase 5: User Story 3 - Redémarrer depuis l'interface (Priority: P2)

**Goal**: le bouton Restart relance l'application sans script externe

**Independent Test**: changer le port OSC, cliquer sur Restart, l'application écoute sur le nouveau port en moins de 10 s, avec une seule fenêtre

- [ ] T032 [US3] Dans `desktop.py`, `relaunch()` : relancer l'exécutable courant (`sys.executable` empaqueté, ou `sys.executable desktop.py` depuis les sources) avec `--wait-lock`, détaché (`start_new_session=True` en POSIX, `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` sous Windows), puis `os._exit(0)` ; l'assigner à `mini_osc.restart_callback` dans `main()`
- [ ] T033 [US3] Dans `desktop.py`, `--wait-lock` : réessayer la prise du verrou toutes les 250 ms pendant 15 s au maximum, puis attendre 2 s avant `start_servers` pour laisser le système libérer les ports (R10)
- [ ] T034 [US3] Vérifier sur le `.app` local : changer le port OSC, Restart, vérifier le nouveau port (`lsof -i UDP:<port>`), une seule fenêtre, moins de 10 s

---

## Phase 6: User Story 4 - Une seule instance à la fois (Priority: P2)

**Goal**: un second lancement ne crée pas de seconde instance et ramène la fenêtre existante

**Independent Test**: lancer deux fois, une seule instance tourne et route toujours

### Tests for User Story 4

- [ ] T035 [P] [US4] Écrire `tests/test_single_instance.py` : `acquire_lock(port)` réussit sur un port libre ; un second `acquire_lock` sur le même port échoue tant que le premier est tenu, et réussit après sa libération ; `notify_existing(port)` envoie `show\n` et l'écouteur appelle le callback (port de test différent de 53999)

### Implementation for User Story 4

- [ ] T036 [US4] Dans `desktop.py`, `acquire_lock(port=53999)` : socket TCP sur `127.0.0.1`, `SO_EXCLUSIVEADDRUSE` sous Windows, jamais `SO_REUSEADDR`, puis `listen` ; un thread `daemon` accepte les connexions et, sur `show\n`, appelle `window.restore()` puis `window.show()` ; `notify_existing(port)` ; faire passer T035
- [ ] T037 [US4] Dans `desktop.py`, `main()` : prendre le verrou avant tout démarrage de serveur ; s'il est pris (et sans `--wait-lock`), `notify_existing` puis `sys.exit(0)` ([contracts/launcher.md](contracts/launcher.md))
- [ ] T038 [US4] Vérifier sur le `.app` local : un second lancement ramène la fenêtre, un seul processus (`pgrep -f Mini-OSC`), le routage fonctionne toujours

---

## Phase 7: User Story 5 - Produire les quatre versions automatiquement (Priority: P2)

**Goal**: un tag `v*` produit et publie quatre fichiers testés, et rien n'est publié si l'un échoue

**Independent Test**: pousser un tag `v2.0.0-rc1`, obtenir quatre jobs verts et une release avec quatre fichiers

- [X] T039 [P] [US5] Créer les icônes `packaging/icons/mini-osc.png` (1024 px), `packaging/icons/mini-osc.icns` (avec `iconutil`) et `packaging/icons/mini-osc.ico`, et les référencer dans `packaging/mini_osc.spec` et `packaging/build_linux.sh`
- [ ] T040 [US5] Étendre `.github/workflows/build.yml` : déclencheurs `push: tags: ['v*']` et `workflow_dispatch` ; matrice `macos-15` (arm64), `macos-15-intel` (intel), `windows-latest` (x64), `ubuntu-22.04` (x86_64) ; Python 3.12 ; `pytest tests/` sur chaque job ; version tirée du tag (sinon `dev`)
- [ ] T041 [US5] Dans `.github/workflows/build.yml`, étape Windows : `pyinstaller packaging/mini_osc.spec`, smoke test de `dist/Mini-OSC.exe --smoke-test`, renommage en `Mini-OSC-$VERSION-windows-x64.exe` (shell `bash`)
- [ ] T042 [US5] Dans `.github/workflows/build.yml`, étapes macOS et Linux : appeler `packaging/build_macos.sh` ou `packaging/build_linux.sh` avec `VERSION` et `ARCH`, puis envoyer chaque livrable en artefact (`actions/upload-artifact`)
- [ ] T043 [US5] Dans `.github/workflows/build.yml`, job `release` (`needs` sur toute la matrice, seulement sur un tag, `permissions: contents: write`) : télécharger les quatre artefacts et `gh release create "$TAG" dist/* --generate-notes` (R14)
- [ ] T044 [US5] Pousser la branche, puis le tag `v2.0.0-rc1` ; vérifier quatre jobs verts et une release avec quatre fichiers (`gh release view v2.0.0-rc1`) ; corriger jusqu'au vert (quickstart section 5)

---

## Phase 8: User Story 6 - La version script continue de fonctionner (Priority: P3)

**Goal**: aucune régression pour les installations script existantes

**Independent Test**: lancer `Start_OSC_Webapp.command` sur une copie d'une installation existante, config chargée, routage et Restart fonctionnels

- [ ] T045 [US6] Vérifier `Start_OSC_Webapp.command` de bout en bout (quickstart section 1) : config du dossier chargée, interface ouverte, Restart par code 42 qui relance la boucle, logs dans `./logs/`
- [ ] T046 [US6] Vérifier `python mini_osc.py` lancé depuis un autre dossier courant : il utilise désormais le `config.json` situé à côté du script ; noter ce changement dans le README

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T047 [P] Mettre à jour `README.md` : téléchargement par plateforme (tableau des quatre fichiers), premier lancement (Gatekeeper sous macOS 15 « Ouvrir quand même » ou `xattr -dr com.apple.quarantine`, SmartScreen, pare-feu), prérequis Linux (`libwebkit2gtk-4.1-0`, `gir1.2-webkit2-4.1`, Ubuntu 22.04+ ou Debian 12+), emplacement de la config et des logs par système, mode script inchangé (FR-016)
- [ ] T048 [P] Mettre à jour `CLAUDE.md` du projet : section « Desktop app » (`desktop.py`, `packaging/`, CI, `DATA_DIR`, `restart_callback`)
- [ ] T049 Tester l'exécutable Windows et l'AppImage x86_64 de la release candidate sur de vraies machines (quickstart section 6), avec l'aide de l'utilisateur
- [ ] T050 Relecture finale : aucun tiret long ni demi-cadratin dans le code, les messages et la documentation ajoutés (recherche des caractères U+2014 et U+2013 avec `grep -rnP "\x{2014}|\x{2013}"`) ; `pytest tests/` vert

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: aucune dépendance
- **Foundational (Phase 2)**: après le Setup ; bloque toutes les stories
- **US1 (Phase 3)**: après la Phase 2 ; c'est le MVP et la base de toutes les autres stories en mode bureau
- **US2 (Phase 4)**: après US1 (réutilise `desktop.py` et la page d'erreur)
- **US3 (Phase 5)** et **US4 (Phase 6)**: après US1 ; T033 (`--wait-lock`) dépend de T036 (verrou), donc faire US4 avant de terminer US3
- **US5 (Phase 7)**: après US1 (le job Linux de T025 sert de base) ; idéalement après US2 à US4 pour que la release candidate soit complète
- **US6 (Phase 8)**: vérifiable dès la fin de la Phase 2
- **Polish (Phase 9)**: à la fin

### Parallel Opportunities

- Phase 1 : T002, T003, T004 et T005 en parallèle
- US1 : T012 et T013 en parallèle ; T022 et T023 en parallèle après T021
- T027 (US2) et T035 (US4) peuvent s'écrire en parallèle
- T039 en parallèle de T040 à T043
- T047 et T048 en parallèle

### Parallel Example: User Story 1

```text
Task: "T012 [US1] tests/test_window_url.py"
Task: "T013 [US1] tests/test_data_dir.py"
puis, après T021 :
Task: "T022 [US1] packaging/build_macos.sh"
Task: "T023 [US1] packaging/build_linux.sh"
```

---

## Implementation Strategy

### MVP First

1. Phases 1 et 2 (moteur pilotable, mode script intact)
2. Phase 3 (US1), dont le **build Linux T025-T026 le plus tôt possible** : c'est le principal risque technique
3. **STOP et validation** : application Mac locale et AppImage Linux verte en CI

### Incremental Delivery

1. US1 puis US2 : application exploitable en salle
2. US4 puis US3 : confort d'exploitation (instance unique, Restart)
3. US5 : release automatique des quatre fichiers
4. US6 et Polish : non-régression, documentation, tests sur vraies machines

---

## Notes

- Les tests sur machines réelles (T049) demandent l'aide de l'utilisateur (PC Windows, machine Linux)
- Raspberry Pi hors périmètre : à ajouter plus tard si besoin (job `ubuntu-22.04-arm`, voir research.md R4)
- Commit après chaque tâche ou groupe logique, sur `feature/desktop-app`
- Aucune modification du routage (`handle_osc_in_message`, `handle_incoming_non_osc`, `send_to_*`) n'est prévue ; si une tâche semble l'exiger, s'arrêter et en parler
