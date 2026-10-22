# Tasks: Destination « Multiball » (API cloud LYMB.iO)

**Input**: Design documents from `specs/002-multiball-api/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: inclus (demandés explicitement : requêtes, séquence `start`, mémoire, secrets, action inconnue ; tout simulé).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallélisable (fichiers différents, aucune dépendance sur une tâche non terminée)
- **[Story]**: user story concernée (US1 à US5)

---

## Phase 1: Setup

- [ ] T001 Créer la branche `feature/multiball-api` et le dossier `specs/002-multiball-api/`
- [ ] T002 [P] Ajouter `"multiball"` à `hiddenimports` dans `packaging/mini_osc.spec` (R9)

---

## Phase 2: Foundational (bloquant)

- [ ] T003 Créer `multiball.py` : constantes (`DEFAULT_BASE_URL`, `REQUEST_TIMEOUT = 10`, `DEFAULT_START_DELAY = 3`, `ACTIONS`), fonction `redact(text, secrets)`, `api_request(target, method, path, body, log)` (auth Basic via `auth=(api_key, token)`, `timeout=10`, retour `ApiResult(ok, status, data, message)`, log `[MULTIBALL] METHOD URL body -> code réponse tronquée` passé par `redact`), helpers `courts_path`, `games_path` (R1, R2)
- [ ] T004 Dans `mini_osc.py`, `expand_connections()` : pour `to.protocol == "multiball"`, recopier `base_url` (défaut), `api_key`, `token`, `court_id`, `start_delay` dans la cible interne
- [ ] T005 Dans `mini_osc.py`, `handle_osc_in_message()` : étendre la correspondance par préfixe aux cibles `multiball`, ne pas appliquer `values`, et appeler `multiball_controller.dispatch(target, sub_address, list(args), route.get("response_to_osc"))` (R5)

**Checkpoint**: le routage atteint le module Multiball sans bloquer.

---

## Phase 3: User Story 1 - Lancer une partie en un message (P1) 🎯 MVP

**Independent Test**: `/mb/start <id>` avec `requests` simulé produit switchGame puis start, avec la pause, la bonne URL et l'auth.

- [ ] T006 [P] [US1] Tests dans `tests/test_multiball.py` : URL, méthode, corps, `auth` et `timeout` de switchGame, setConfiguration, start, stop (barre finale), GET court ; en-tête Basic produit = `base64(key:token)`
- [ ] T007 [P] [US1] Tests dans `tests/test_multiball.py` : séquence `start` sans réglage, avec réglage (durée seule, difficulté seule, les deux), nouvelle tentative unique après échec, arrêt si switchGame échoue, `dispatch` rend la main immédiatement (thread)
- [ ] T008 [US1] Dans `multiball.py`, classe `Controller(log, send_osc, sleep_event_factory)` : `parse(sub_address, args)`, `dispatch()` (thread démon), `_run_start()` avec pause annulable `Event.wait(delay)` et une nouvelle tentative (R3, data-model « Séquence start »)
- [ ] T009 [US1] Dans `multiball.py`, validation des arguments (`gameId`, `duration`, `difficulty`) et de la connexion (clé, jeton, terrain), `start_delay` borné 0 à 60 (R8)

---

## Phase 4: User Story 2 - Actions unitaires, mémoire, statut (P1)

**Independent Test**: `/mb/start <id>` puis `/mb/stop` arrête `<id>` ; `/mb/stop` sans mémoire lit le terrain.

- [ ] T010 [P] [US2] Tests dans `tests/test_multiball.py` : `switch`, `play` avec et sans gameId, `stop` avec mémoire, `stop` sans mémoire (lecture du terrain), `stop` sans jeu en cours, `status`, action inconnue, préfixe seul, gameId manquant (aucun appel), annulation d'un `start` en pause par `stop`
- [ ] T011 [US2] Dans `multiball.py`, état par `(base_url, court_id)` (`last_loaded`, `last_started`, `cancel_event`) protégé par un verrou ; actions `switch`, `play`, `stop`, `status` ; repli sur `GET /courts/{id}` (R4)

---

## Phase 5: User Story 5 - Les secrets ne fuient pas (P1)

**Independent Test**: un jeton reconnaissable n'apparaît dans aucun log, ni dans `/get_config`, ni dans l'export par défaut.

- [ ] T012 [P] [US5] Tests dans `tests/test_multiball.py` : jeton absent des logs (succès, erreur HTTP, exception réseau dont le message contiendrait le jeton) ; `/get_config` masque et indique `token_set` ; `update_connection` avec jeton vide garde l'ancien ; export sans jeton par défaut et avec `include_secrets=1` ; import qui reprend le jeton par clé API ; `config.default.json` sans `token`
- [ ] T013 [US5] Dans `multiball.py` : `mask_config(cfg)`, `strip_tokens(cfg)`, `keep_tokens(new_cfg, old_cfg)` (par index pour update, par `api_key` pour import)
- [ ] T014 [US5] Dans `mini_osc.py` : brancher `/get_config` (masque), `/add_connection` et `/update_connection` (retrait de `token_set`, conservation du jeton), `/export_config` (`include_secrets`), `/import_config` (reprise des jetons) ; `validate_config()` complète `base_url` et `start_delay` des connexions Multiball (R6)

---

## Phase 6: User Story 3 - Retour vers COGS (P2)

**Independent Test**: retour activé, échec simulé, réception de `[action, 0, message]`.

- [ ] T015 [P] [US3] Tests dans `tests/test_multiball.py` : retour `start 1`, `start 0 <message API>`, `status 1 <status> <nom> <id>`, retour sur action inconnue, pas de retour si désactivé ou incomplet
- [ ] T016 [US3] Dans `multiball.py`, `_feedback(resp_cfg, args)` qui appelle `send_osc` injecté et journalise ; erreurs d'envoi attrapées (R7)

---

## Phase 7: User Story 4 - Interface et « Test and list » (P2)

**Independent Test**: avec `requests` simulé, `/multiball_list` renvoie terrains puis jeux ; erreur API affichée telle quelle.

- [ ] T017 [P] [US4] Tests dans `tests/test_multiball.py` : `/multiball_list` courts, games, erreur 401 avec message, requête incomplète (400), usage du jeton et de l'adresse enregistrés quand `token` vide et `index` fourni
- [ ] T018 [US4] Dans `mini_osc.py`, route `POST /multiball_list` (lecture seule) (contracts/http-endpoints.md)
- [ ] T019 [US4] Dans `index.html` : option « Multiball (LYMB API) », champs (`to_mb_base_url`, `to_mb_api_key`, `to_mb_token` masqué, `to_mb_court_id`, `to_mb_start_delay`), retour OSC (mêmes champs que HTTP), `buildConnectionFromForm`, `editConnection` (jeton vide + indication « token saved »), refus d'une source non OSC, préfixe `/mb` proposé
- [ ] T020 [US4] Dans `index.html` : bouton « Test and list », liste des terrains cliquables (remplit `court_id` et charge les jeux), liste des jeux (id, nom, versions) avec bouton copier, messages d'erreur tels quels
- [ ] T021 [US4] Dans `index.html` : aide-mémoire des messages OSC (préfixe dynamique), affichage `MULTIBALL` dans la table (terrain, ↩ OSC), style `proto-tag-multiball`
- [ ] T022 [US4] Dans `index.html` : export avec case « Include Multiball tokens » et confirmation d'avertissement

---

## Phase 8: Polish

- [ ] T023 [P] `README.md` : section Multiball (config, messages OSC, retour, Test and list, secrets, mode script et `config.json` suivi par git)
- [ ] T024 [P] `CLAUDE.md` : section « Multiball destination » comme « Raw JSON destination »
- [ ] T025 Lancer `python -m pytest tests` et `python desktop.py --smoke-test` ; tout passe
- [ ] T026 Vérifier par grep : aucun tiret long ni demi-cadratin dans les fichiers modifiés, aucun jeton dans le dépôt
- [ ] T027 Vérification visuelle de l'interface (formulaire, Test and list avec API simulée, table)

---

## Dependencies & Execution Order

- Phase 1 et 2 avant tout. US1 avant US2 (même module, la séquence `start` sert de base). US5, US3, US4 dépendent de T003 et T013 mais pas entre elles, sauf T019 à T022 qui supposent T014 et T018.
- Polish en dernier.

## Parallel Example

```text
T006, T007, T010, T012, T015, T017 (tests) peuvent être écrits ensemble dans un même fichier, en un passage.
T023 et T024 (docs) en parallèle.
```

## Implementation Strategy

MVP = Phases 1 à 4 (lancer et arrêter depuis COGS), puis secrets (P1), retour, interface, docs. Chaque phase se termine par `pytest`.
