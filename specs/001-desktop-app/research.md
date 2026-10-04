# Research: Mini-OSC en logiciel de bureau autonome

Chaque décision suit le format Décision / Justification / Alternatives écartées.

## R1. Empaquetage Python

- **Décision**: PyInstaller (6.x), un build par plateforme, sur la plateforme elle-même.
- **Justification**: garde `mini_osc.py` tel quel, embarque Python et les dépendances, hooks maintenus pour pywebview, pythonnet et PyGObject (`pyinstaller-hooks-contrib`). Pas de compilation croisée : chaque plateforme a son runner.
- **Alternatives écartées**: Nuitka (compilation C plus longue, hooks GUI moins éprouvés) ; Briefcase (impose sa structure de projet) ; réécriture Electron/Tauri (réinvente ce qui marche, hors demande).

## R2. Fenêtre native

- **Décision**: pywebview 5.x, qui affiche l'URL du serveur Flask local. Backends : Cocoa/WebKit (macOS), EdgeChromium/WebView2 (Windows), GTK/WebKit2GTK 4.1 (Linux).
- **Justification**: fenêtre de vraie application sans embarquer de navigateur (fichiers de 30 à 60 Mo au lieu de 150 Mo et plus). L'interface actuelle est servie sans modification.
- **Alternatives écartées**: backend Qt/QtWebEngine (environ 200 Mo, roues ARM incertaines) ; ouvrir le navigateur par défaut (pas une vraie fenêtre, et fermer l'onglet ne quitterait pas le logiciel).

## R3. Forme du livrable par plateforme

| Plateforme | Runner GitHub | Mode PyInstaller | Livrable |
|---|---|---|---|
| macOS Apple Silicon | `macos-15` (arm64) | `--windowed` onedir dans `.app` | `Mini-OSC-<ver>-macos-arm64.dmg` |
| macOS Intel | `macos-15-intel` (x86_64) | idem | `Mini-OSC-<ver>-macos-intel.dmg` |
| Windows | `windows-latest` (x64) | `--onefile --windowed` | `Mini-OSC-<ver>-windows-x64.exe` |
| Linux x86_64 | `ubuntu-22.04` | onedir puis AppDir | `Mini-OSC-<ver>-linux-x86_64.AppImage` |

- **Justification**: PyInstaller déconseille `--onefile` dans un `.app` macOS, d'où onedir dans le bundle, lui-même emballé dans un `.dmg` (`hdiutil`). Sous Windows, `--onefile` donne le fichier unique demandé, au prix de 1 à 3 s d'extraction au lancement (compatible avec SC-002). Sous Linux, le format AppImage donne un fichier unique.
- **Alternatives écartées**: binaire macOS `universal2` (nécessite que toutes les extensions compilées, dont pyobjc, soient universelles, donc plus fragile) ; installateur Windows Inno Setup (un fichier unique suffit pour l'usage visé, l'installateur peut venir plus tard).
- **Note runners**: `macos-13` a été retiré ; `macos-15-intel` est le runner Intel actuel. Dépôt public, donc runners gratuits.

## R4. Linux : compatibilité glibc et WebKitGTK

- **Décision**: construire sur Ubuntu 22.04 (glibc 2.35), x86_64. Ne pas embarquer GTK ni WebKitGTK : ils sont fournis par le système cible (`libwebkit2gtk-4.1-0`, `gir1.2-webkit2-4.1`). PyGObject épinglé `<3.51` (la 3.51 et plus exige `girepository-2.0`, absent de 22.04).
- **Justification**: un binaire lié à glibc 2.35 tourne sur Ubuntu 22.04+, Debian 12+ et les distributions de bureau récentes. Construire sur 24.04 (glibc 2.39) exclurait les systèmes un peu plus anciens. Ce choix garde aussi la porte ouverte à une future version Raspberry Pi (Pi OS Bookworm, glibc 2.36). Embarquer WebKitGTK alourdit fortement le fichier et entre en conflit avec les thèmes et pilotes graphiques du système.
- **Risque**: le hook PyInstaller de `gi` collecte par défaut des bibliothèques GTK. Il faudra peut-être les exclure pour forcer l'usage de celles du système. **À valider tôt par un build CI Linux et un test sur une vraie machine Linux.**
- **Alternatives écartées**: build sur 24.04 (glibc trop récente pour une partie des systèmes) ; Flatpak (installation plus lourde, pas un fichier unique).

## R5. AppImage sans libfuse2

- **Décision**: `appimagetool` récent (projet `AppImage/appimagetool`, runtime type 2 statique), version x86_64.
- **Justification**: l'ancien runtime exige `libfuse2`, absent par défaut d'Ubuntu 22.04+. Le runtime statique n'en a plus besoin.
- **Alternatives écartées**: documenter `sudo apt install libfuse2` (friction inutile) ; archive `.tar.gz` (pas un fichier lançable d'un double-clic).

## R6. Dossier de données utilisateur

- **Décision**: petite fonction locale, sans dépendance :
  - macOS : `~/Library/Application Support/Mini-OSC`
  - Windows : `%APPDATA%\Mini-OSC`
  - Linux : `$XDG_CONFIG_HOME/mini-osc`, sinon `~/.config/mini-osc`
  - Surcharge possible par la variable d'environnement `MINI_OSC_DATA_DIR` (tests, cas particuliers).
- **Justification**: trois cas simples, la dépendance `platformdirs` n'apporte rien de plus ici.
- **Mode script**: le dossier de données reste le dossier du script (FR-015). Aujourd'hui `CONFIG_FILE = "config.json"` est relatif au dossier courant ; `Start_OSC_Webapp.command` fait un `cd` dans le dossier du script, donc le rendre relatif au script ne change rien pour les installations existantes.

## R7. Configuration par défaut

- **Décision**: nouveau fichier `config.default.json` embarqué (OSC `127.0.0.1:53000`, HTTP `127.0.0.1:5009` (5000 est pris par AirPlay sur macOS récent), aucune connexion, journalisation fichier désactivée), copié dans le dossier de données s'il n'y a pas de `config.json`.
- **Justification**: le `config.json` du dépôt contient des connexions de test et des IP du réseau de développement : il ne doit pas devenir la configuration d'un opérateur.
- **Configuration illisible**: `load_config` lèvera une exception `ConfigError` au lieu d'appeler `sys.exit(1)`. Le mode script l'attrape et sort avec le même message et le même code qu'aujourd'hui ; le mode bureau l'affiche dans la fenêtre. Le fichier n'est jamais réécrit si la lecture échoue.

## R8. Ressources hors ligne

- **Décision**: copier `bulma.min.css` (0.9.3) et `font-awesome/all.min.js` (5.15.4, version SVG+JS autonome, sans polices à charger) dans `vendor/`, et pointer les deux balises de `index.html` sur ces copies.
- **Justification**: mêmes versions exactes que le CDN actuel, donc rendu identique. La version JS de Font Awesome embarque les icônes en SVG : aucun fichier de police supplémentaire.
- **Alternatives écartées**: inliner les fichiers dans `index.html` (fichier illisible, diff énorme).

## R9. Instance unique

- **Décision**: verrou par socket TCP en écoute sur `127.0.0.1:53999`. Si le port est pris, une autre instance tourne : on lui envoie `show` sur cette socket (elle remet sa fenêtre au premier plan), puis on quitte. Sous Windows, option `SO_EXCLUSIVEADDRUSE` ; jamais `SO_REUSEADDR`.
- **Justification**: le système libère la socket si le processus meurt, donc pas de verrou orphelin (contrairement à un fichier verrou). Le même canal sert à ramener la fenêtre.
- **Alternatives écartées**: fichier verrou (orphelin après un crash) ; mutex nommé Windows (spécifique à un système).

## R10. Bouton Restart

- **Décision**: point d'accroche `restart_callback` dans `mini_osc.py`. S'il est défini (mode bureau), `/restart` lance une nouvelle instance de l'exécutable avec `--wait-lock` (processus détaché), puis quitte l'instance courante. La nouvelle instance réessaie le verrou pendant 15 s au maximum avant de démarrer. Sans point d'accroche (mode script), le comportement actuel (code de sortie 42) est conservé à l'identique.
- **Justification**: redémarrer les serveurs à l'intérieur du même processus demanderait d'arrêter proprement les threads TCP/UDP et Flask, qui tournent aujourd'hui en boucle infinie, donc de modifier le moteur. Relancer le processus réutilise exactement le chemin de démarrage normal.
- **Risque**: un port TCP avec des connexions récemment fermées peut rester en `TIME_WAIT` quelques secondes. Le script actuel a la même limite (pause de 2 s). On garde une pause équivalente avant le démarrage des serveurs.

## R11. Erreurs de démarrage visibles

- **Décision**: dans le mode bureau, les serveurs démarrent dans un thread. Le lanceur attend que le port HTTP réponde (jusqu'à 15 s). En cas d'échec (exception, `ConfigError`, port occupé), la fenêtre affiche une page d'erreur HTML locale avec le message et le chemin du fichier de configuration, au lieu d'une fenêtre vide.
- **URL de la fenêtre**: `http://<flask_ip>:<port>/`. Si `flask_ip` vaut `0.0.0.0` ou `::`, on utilise `127.0.0.1`.

## R12. Fermeture

- **Décision**: `webview.start()` rend la main quand la fenêtre est fermée. Le lanceur appelle alors `os._exit(0)`, ce qui arrête tous les threads (déjà `daemon`) et libère les ports.
- **Justification**: Flask (`app.run`) n'a pas d'arrêt propre depuis un autre thread. La sortie du processus est le moyen fiable et immédiat (FR-006).

## R13. Tests et vérification en CI

- **Décision**:
  - `pytest` pour les nouvelles fonctions pures (dossier de données, configuration par défaut, URL de la fenêtre, verrou d'instance, `ConfigError`).
  - Option `--smoke-test` de l'exécutable : démarre les serveurs sans fenêtre dans un dossier de données temporaire, vérifie que `GET /` et `GET /vendor/bulma.min.css` répondent 200, puis sort avec le code 0 ou 1. Lancée en CI sur chaque livrable juste après le build, donc sur les quatre plateformes.
  - Vérification manuelle de la fenêtre sur chaque système.
- **Justification**: les runners n'ont pas d'écran ; le smoke test vérifie au moins que le binaire empaqueté démarre et sert l'interface.

## R14. Publication

- **Décision**: workflow `.github/workflows/build.yml` déclenché par un tag `v*` (et à la main). Matrice de quatre jobs ; chaque job construit, lance le smoke test, téléverse son livrable. Un job final, qui ne tourne que si les quatre ont réussi, crée la release GitHub avec les quatre fichiers (`gh release create`).
- **Justification**: SC-006 (aucune intervention au-delà du tag) et scénario US5-2 (rien de publié si un build échoue).

## R15. Premier lancement sur Mac non signé

- **Constat**: PyInstaller signe automatiquement en ad hoc (obligatoire sur Apple Silicon). Depuis macOS 15 (Sequoia), le contournement par clic droit puis Ouvrir a disparu : il faut passer par Réglages Système, Confidentialité et sécurité, « Ouvrir quand même ». Autre solution : `xattr -dr com.apple.quarantine /Applications/Mini-OSC.app`.
- **Décision**: documenter les deux méthodes dans le README.
