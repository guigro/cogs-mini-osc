# Contract: lanceur bureau (`desktop.py` / exécutable Mini-OSC)

## Invocation

```text
Mini-OSC [--wait-lock] [--smoke-test]
```

| Option | Effet |
|---|---|
| (aucune) | Lancement normal : verrou, serveurs, fenêtre |
| `--wait-lock` | Utilisée par le Restart : réessaie de prendre le verrou pendant 15 s au maximum au lieu d'abandonner tout de suite |
| `--smoke-test` | Sans fenêtre : démarre les serveurs dans un dossier de données temporaire, vérifie `GET /` et `GET /vendor/bulma.min.css` (200), puis sort |

## Variables d'environnement

| Variable | Effet |
|---|---|
| `MINI_OSC_DATA_DIR` | Remplace le dossier de données par défaut |

## Codes de sortie

| Code | Cas |
|---|---|
| 0 | Fenêtre fermée normalement ; smoke test réussi ; seconde instance qui a passé la main à la première |
| 1 | Smoke test échoué ; erreur fatale avant l'ouverture de la fenêtre |

Le mode script (`python mini_osc.py`) garde ses codes actuels : 1 si la configuration est invalide, 42 pour le Restart.

## Canal d'instance unique

- Écoute TCP sur `127.0.0.1:53999`, réservée au premier processus.
- Message accepté : `show\n`, qui remet la fenêtre au premier plan. Tout autre message est ignoré.
- La seconde instance envoie `show\n` puis sort avec le code 0.

## Fenêtre

- Titre : `Mini-OSC`. Taille initiale 1280 x 860, redimensionnable.
- URL : `http://<flask_server.ip>:<flask_server.port>/`, avec `127.0.0.1` à la place de `0.0.0.0` ou `::`.
- Si les serveurs ne démarrent pas dans les 15 s, ou en cas d'erreur, une page d'erreur locale affiche le message et le chemin de `config.json`.
- Fermer la fenêtre termine le processus.

## Point d'accroche dans `mini_osc.py`

- `mini_osc.set_data_dir(path)` : à appeler avant `start_servers`.
- `mini_osc.start_servers(run_flask=True)` : démarre OSC, TCP/UDP et Flask (bloquant si `run_flask`). Lève `ConfigError` si la configuration est invalide.
- `mini_osc.restart_callback` : si défini, `POST /restart` l'appelle à la place de `os._exit(42)`.
