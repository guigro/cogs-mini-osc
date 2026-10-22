# Implementation Plan: Destination « Multiball » (API cloud LYMB.iO)

**Branch**: `feature/multiball-api` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-multiball-api/spec.md`

## Summary

Ajouter un type de destination `multiball` aux connexions dont la source est OSC. Toute la logique d'API vit dans un nouveau module `multiball.py` (construction des requêtes, actions, enchaînement de `start`, mémoire par terrain, annulation, retour OSC, masquage des secrets). `mini_osc.py` ne fait que brancher ce module : correspondance par préfixe (comme OSC vers OSC), lancement de l'action dans un thread, masquage du jeton dans `/get_config` et l'export, conservation du jeton à l'enregistrement et à l'import, et une route de lecture `/multiball_list` pour le bouton « Test and list ». L'interface (`index.html`) gagne un formulaire Multiball, la liste des terrains et des jeux, et un aide-mémoire.

## Technical Context

**Language/Version**: Python 3.12 (builds) et Python du mode script ; JavaScript sans framework dans `index.html` (Bulma)

**Primary Dependencies**: existantes uniquement (Flask, requests, python-osc). Aucune nouvelle dépendance.

**Storage**: `config.json` (dossier de données) ; la mémoire du dernier jeu est en RAM (non persistée)

**Testing**: pytest, `requests` simulé via monkeypatch ; aucun appel réseau réel

**Target Platform**: identique à l'existant (script, app de bureau macOS, Windows, Linux)

**Project Type**: pont de protocoles (serveur local + interface web)

**Performance Goals**: le traitement d'un message OSC Multiball rend la main en quelques millisecondes (thread) ; 10 s maximum par requête API

**Constraints**: jamais de jeton ni d'en-tête Authorization dans les logs ; aucun identifiant dans le dépôt ; aucune régression des connexions existantes ; aucun tiret long ni demi-cadratin

**Scale/Scope**: 1 nouveau module (~300 lignes), ~80 lignes dans `mini_osc.py`, ~250 lignes dans `index.html`, 1 fichier de tests, README, CLAUDE.md

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` est encore le modèle vierge : aucune barrière formelle. Contraintes de l'utilisateur appliquées :

| Contrainte | Respect dans ce plan |
|---|---|
| Ne pas casser l'existant ni la migration | Seuls ajouts dans le moteur ; la correspondance par préfixe est étendue au seul type `multiball` ; tests existants conservés |
| Aucun appel qui change l'état du mur sans accord | Tests 100 % simulés ; seule la route de lecture peut être essayée en réel avec la clé de l'utilisateur |
| Aucun secret dans les logs, l'interface, le dépôt | Masquage centralisé dans `multiball.py`, tests dédiés |
| Pas de tiret long ni demi-cadratin | Vérifié par grep avant commit |

Revérification après la phase 1 : conforme.

## Project Structure

### Documentation (this feature)

```text
specs/002-multiball-api/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── osc-messages.md      # Messages OSC entrants et retour vers COGS
│   └── http-endpoints.md    # Routes Flask nouvelles ou modifiées
└── tasks.md
```

### Source Code (repository root)

```text
multiball.py              # NOUVEAU : client API, actions, séquence start, mémoire, secrets
mini_osc.py               # branchement routage, /get_config, export/import, /multiball_list
index.html                # formulaire, Test and list, aide-mémoire, affichage dans la table
packaging/mini_osc.spec   # hiddenimports += "multiball"
tests/test_multiball.py   # NOUVEAU
README.md, CLAUDE.md
```

**Structure Decision**: module séparé pour que la logique soit testable sans démarrer les serveurs, et pour garder `mini_osc.py` lisible. Le module ne dépend pas de `mini_osc` (pas d'import circulaire) : les fonctions de log et d'envoi OSC lui sont injectées.

## Complexity Tracking

Aucune violation à justifier.
