# Data Model: Mini-OSC en logiciel de bureau autonome

Aucun nouveau format de données : on ne change que l'emplacement des fichiers existants, et on ajoute une configuration par défaut.

## Dossier de données (DataDir)

| Mode de lancement | Emplacement |
|---|---|
| Script (`python mini_osc.py`) | Dossier contenant `mini_osc.py` |
| Bureau, macOS | `~/Library/Application Support/Mini-OSC/` |
| Bureau, Windows | `%APPDATA%\Mini-OSC\` |
| Bureau, Linux | `$XDG_CONFIG_HOME/mini-osc/`, sinon `~/.config/mini-osc/` |
| Toute plateforme, surcharge | Valeur de la variable `MINI_OSC_DATA_DIR` (prioritaire en mode bureau) |

Contenu :

```text
<DataDir>/
├── config.json        # Configuration (format existant, inchangé)
└── logs/
    ├── mini_osc.log   # Log du jour (si file_logging.enabled)
    └── mini_osc.log.YYYY-MM-DD
```

Règles :
- Le dossier est créé s'il n'existe pas.
- Il n'est jamais remplacé par une mise à jour de l'application (il est hors du bundle).

## Configuration (`config.json`)

Format existant, inchangé : `osc_server`, `flask_server`, `connections[]`, `ignore_rules[]`, `file_logging`. L'ancien format `targets` + `routes` est toujours migré automatiquement au chargement.

Cycle de vie au démarrage en mode bureau :

```text
absent  ──copie de config.default.json──▶  présent
présent ──lecture OK──▶ migration éventuelle ──▶ enregistrement ──▶ chargé
présent ──lecture KO (JSON invalide, section manquante)──▶ ConfigError
         ──▶ fenêtre d'erreur, fichier laissé intact
```

Validation (existante, conservée) : `osc_server` présent, `flask_server` présent, `connections` est une liste. `file_logging` est complété par défaut s'il manque.

## Configuration par défaut (`config.default.json`)

```json
{
    "osc_server": { "listen_ip": "127.0.0.1", "listen_port": 53000 },
    "flask_server": { "ip": "127.0.0.1", "port": 5000 },
    "connections": [],
    "ignore_rules": [],
    "file_logging": { "enabled": false, "retention_days": 7, "log_level": "DEBUG" }
}
```

## Verrou d'instance (état en mémoire)

| État | Signification |
|---|---|
| Libre | Le port `127.0.0.1:53999` n'est pas en écoute : aucune instance |
| Tenu | L'instance courante écoute sur ce port et répond à `show` |

Transitions : démarrage (libre vers tenu) ; arrêt ou crash du processus (tenu vers libre, libéré par le système).
