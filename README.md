# Imapsync CLI

Lokální migrace IMAP schránek přes Docker, s konfigurací v JSONu a průvodcem
v terminálu. Podporuje výběr více účtů, kontrolu přihlášení, velikosti složek,
zkušební průchod, práci se složkami i skutečný přenos. Webové UI není součástí.

## Požadavky

- macOS, Bash, Git a Python 3.9 nebo novější. Projekt je ověřený na macOS;
  používá Unixové knihovny `fcntl` a `curses`, nativní Windows nepodporuje.
- Spuštěný [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/)
  s Docker Compose. Případný Python instalujte z [python.org](https://www.python.org/downloads/macos/).
- Existující zdrojová i cílová schránka, dostupné přes přímé SSL/TLS,
  obvykle na portu 993. STARTTLS a OAuth nejsou v tomto obalu implementované.

Python nevyžaduje žádné balíčky přes pip. Bash spouští Python, samotný imapsync
běží v jednorázovém kontejneru. Image používá AMD64; na Apple Silicon se spouští
přes podporu této architektury v Docker Desktopu.

## Instalace z GitHubu na novém počítači

Adresu repozitáře v příkladu nahraďte svou skutečnou adresou:

```sh
mkdir -p ~/local-docker
cd ~/local-docker
git clone https://github.com/mezerap/imapsync-docker.git imapsync-migration
cd imapsync-migration
```

Ověřte nástroje a spusťte Docker Desktop:

```sh
python3 --version
git --version
docker compose version
docker info
```

V **nově naklonované** složce vytvořte místní konfiguraci a adresáře:

```sh
cp accounts.example.json accounts.json
mkdir -p passwords logs
chmod 700 passwords logs
chmod 600 accounts.json
chmod +x migrate.sh migrate.py
docker compose pull imapsync
./migrate.sh --help
```

`cp` neopakujte nad již vyplněným `accounts.json`: přepsal by vaše účty.
GitHub záměrně neobsahuje skutečné účty, hesla ani logy. Na novém počítači je
musíte doplnit sami nebo obnovit ze své soukromé zálohy.

## Přidání schránky

Upravte anonymní vzor v `accounts.json`. Například:

```json
[
  {
    "id": "prvni-schranka",
    "enabled": false,
    "source": {
      "host": "imap.old.example.com",
      "port": 993,
      "user": "schranka@example.com",
      "password_file": "prvni-source.txt"
    },
    "target": {
      "host": "imap.new.example.com",
      "port": 993,
      "user": "schranka@example.com",
      "password_file": "prvni-target.txt"
    },
    "automap": false,
    "addheader": true,
    "folder_map": {}
  }
]
```

Servery a uživatelská jména nahraďte skutečnými údaji. Vytvořte soubory
`passwords/prvni-source.txt` a `passwords/prvni-target.txt` a do každého zapište
jen příslušné heslo na první řádek, bez uvozovek nebo dalších poznámek.

```sh
chmod 600 passwords/prvni-source.txt passwords/prvni-target.txt
```

Hesla nevkládejte do JSONu ani do příkazové řádky. Další schránku přidáte jako
další objekt do stejného seznamu, oddělený čárkou, s unikátním `id` a vlastními
soubory hesel. Po novém spuštění průvodce se objeví automaticky.

### Význam nastavení

| Položka | Význam |
| --- | --- |
| `id` | Unikátní název účtu, 1–64 písmen/číslic, `_` nebo `-`; první znak je písmeno/číslice. |
| `enabled` | Zařazení do automatického `--all`. Ručně lze vybrat i vypnutý účet, jen pro daný běh. Výchozí `false`. |
| `source`, `target` | Zdrojový/cílový server (`host`), uživatel (`user`), port (výchozí `993`) a `password_file`. |
| `password_file` | Samotný název souboru v `passwords/`, bez cesty. |
| `automap` | Automatický odhad mapování systémových složek; výchozí `false`. |
| `folder_map` | Přesná pravidla zdroj → cíl; mají přednost před automatickým mapováním. Výchozí `{}`. |
| `separator2` | Volitelný jednoznakový oddělovač hierarchie cílového serveru. Hodnotu určuje cílový server; například tečka nebo svislá čára. |
| `addheader` | Doplnění identifikační hlavičky u zpráv bez ní při přenosu; při vynechání výchozí `false`, vzor používá `true`. |

JSON nepodporuje komentáře. Neznámé položky se odmítají. Jedna konfigurace
nepřijímá libovolné vlastní přepínače imapsync.

### Přesné mapování složek

Příklad pro převod variant složek do ploché struktury cíle:

```json
"automap": false,
"folder_map": {
  "INBOX": "INBOX",
  "Drafts": "drafts",
  "Sent": "sent",
  "Sent Items": "sent",
  "Sent Messages": "sent",
  "Archive": "archive",
  "Archives": "archive",
  "Spam": "spam",
  "Junk": "spam",
  "Deleted Items": "trash",
  "Deleted Messages": "trash",
  "Trash": "trash",
  "Trash/2023": "trash",
  "Notes": "Notes"
}
```

Tento fragment vložte do příslušného objektu účtu. Není to univerzální profil:
nejprve ověřte názvy na obou serverech. Více zdrojových složek se zde slučuje
do jedné cílové, včetně roční podsložky Koše. Pro běžný automatický odhad lze
použít `automap: true`; výsledek vždy zkontrolujte zkušebním průchodem.

## Průvodce v terminálu

```sh
./migrate.sh
```

- **↑/↓** (nebo `j`/`k`): pohyb.
- **Mezerník**: označení/odznačení účtu; lze vybrat více účtů.
- **a**: označit/odznačit všechny účty.
- **Enter**: potvrzení; bez označení účtů zvolí aktuální řádek.
- **q**, **Esc** nebo **Ctrl+C**: ukončení.

Po účtech vyberete režim a zkontrolujete souhrn včetně mapování. Výchozí režim
je simulace. V poslední nabídce je u skutečných změn výchozí **Zrušit**.
Průvodce neupravuje `accounts.json` ani soubory hesel. V terminálu bez vhodného
`TERM` zůstává číselná nabídka; mimo interaktivní terminál použijte přímé argumenty.
Stejné nabídky otevře i `python3 migrate.py`.

| Režim | Přepínač imapsync | Chování |
| --- | --- | --- |
| `check` | `--justlogin` | Jen ověření přihlášení. |
| `sizes` | `--justfoldersizes` | Složky, počty a velikosti zpráv. |
| `dry-run` | `--dry` | Porovnání a simulace, bez přenosu. |
| `folders-dry-run` | `--justfolders --dry` | Náhled mapování/vytvoření složek bez změn. |
| `folders` | `--justfolders` | Skutečně vytváří složky, bez přenosu zpráv. |
| `sync` | Bez těchto omezení | Skutečný přenos zpráv. |
| `plan` | Příkaz se nespouští | Jen vypíše příkaz, bez Dockeru a připojení. |

Pro první schránku použijte postupně **check → dry-run → sync** a potom další
dry-run. Po posledním průchodu by již přenesené zprávy měly být přeskočené.
Ve zkušebním režimu nelze plně simulovat obsah složky, která na cíli ještě
neexistuje; samostatné vytvoření složek už představuje skutečnou změnu.

## Přímé spuštění a více účtů

Spouštěč předává argumenty Pythonu, například:

```sh
./migrate.sh --account prvni-schranka --mode check
./migrate.sh --account prvni-schranka --mode sizes
./migrate.sh --account prvni-schranka --mode dry-run
./migrate.sh --account prvni-schranka --mode folders-dry-run
./migrate.sh --all --mode dry-run
```

Záměrné spuštění režimů se změnami:

```sh
./migrate.sh --account prvni-schranka --mode folders
./migrate.sh --account prvni-schranka --mode sync
```

**Přímé argumenty nevyvolají potvrzovací otázku.** Bez `--mode` je při přímém
výběru účtu výchozí `plan`. `--all` zahrne pouze `enabled: true`; ruční výběr
v průvodci i `--account` funguje jednorázově i při `false`.

Pro oddělené místní konfigurace používejte ignorovaný adresář `configs/`:

```sh
./migrate.sh --config configs/klient.json
./migrate.sh --config configs/klient.json --account prvni-schranka --mode plan
```

Relativní `--config` se počítá od aktuálního pracovního adresáře. Hesla a logy
zůstávají vždy v `passwords/` a `logs/` vedle programu.

## Logy, opakování a omezení

Výstup obsahuje jednotlivé přenosy/přeskočení, ID, velikosti, rychlost, chyby
a závěrečné statistiky. Každý běh uloží log do `logs/` s id účtu, režimem a časem
UTC v názvu. Logy mohou obsahovat soukromá metadata; ladicí režimy mohou odhalit
více údajů. Hesla se do kontejneru připojují jako soubory pouze pro čtení.

Při opakování zachovejte mapování a způsob identifikace zpráv. Imapsync porovnává
Message-Id/Received a již existující zprávy obvykle přeskočí. Skript vždy přidává
`--nosyncduplicates`. Nezapíná mazání zpráv ani složek; může synchronizovat
příznaky. Složky Koš/Spam se řídí retenčními pravidly poskytovatele.

Celý výběr účtů se ověří před prvním připojením. Dávka běží postupně a první
chyba ji zastaví. `.migration.lock` brání souběžným úlohám spuštěným tímto
skriptem ve stejném projektu; nehlídá jiné kopie projektu či ruční Docker běhy.
Terminál nechte otevřený, Docker spuštěný a počítač vzhůru. Ukončení klienta
není potvrzení dokončení přenosu; před opakováním zkontrolujte log a kontejnery.

## Aktualizace a opětovné použití

Až nebude běžet žádná úloha, aktualizujte kód:

```sh
git pull --ff-only
docker compose pull imapsync
```

Místní ignorované účty, hesla a logy zůstávají mimo Git. Pokud Git hlásí místní
změny programu, nejprve je vyřešte; příkaz `reset --hard` zde nepoužívejte.

Image je připnutý na ověřený digest verze 2.326. `pull` stáhne verzi určenou
Compose, **nepřepne ji automaticky na nejnovější imapsync**. Změna digestu
vyžaduje ověření kompatibility `patches/IMAPClient.pm` a testů; nepřepisujte ho
naslepo na `latest`. Tato knihovna zachovává bajtovou délku APPEND při Unicode
vstupu a zakazuje slepé opakování zápisu po nejasné odpovědi. Původ a podmínky
převzatého kódu jsou v [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Kontejnery používají `--rm` a po běhu se odstraní, image zůstává. Data jsou
bind mounty v projektu: `docker compose down -v` nesmaže místní hesla ani logy.
Úplné odstranění adresáře smaže i místní data a obnovovací zálohy; nepatří do
běžné aktualizace.

## Ověření bez připojení ke schránkám

```sh
./migrate.sh --help
docker compose config --quiet
python3 -B -m unittest discover -s tests -p 'test_*.py'
```

Testy ověřují nabídky, více účtů, režimy, bezpečné zrušení a souběhový zámek.
Regresi bajtové délky APPEND lze ověřit na umělých datech v kontejneru:

```sh
docker compose run --rm -T --entrypoint perl \
  --volume "$PWD/tests:/tests:ro" imapsync /tests/append-octets.t
```

Žádný z těchto testů se nepřihlašuje ke schránkám ani nemigruje zprávy.

## Co patří do GitHubu

Verzujte program, Compose, anonymní vzor, testy, dokumentaci a potřebnou opravu
knihovny. `.gitignore` vynechává skutečné `accounts*.json`, `configs/`, hesla,
logy včetně `logs/recovery/`, místní `MIGRATION.md`, předávací kontext,
prostředí a dočasné soubory. Výjimkou je `accounts.example.json` a prázdné
`.gitkeep` v datových adresářích, aby se vytvořily i po klonování.

`.gitignore` neodstraní soubor, který byl již dříve zapsaný v historii Gitu.
Skutečné údaje nepřidávejte pomocí `git add -f` ani do příkladů a README.
Ignorované soubory si případně zálohujte soukromě mimo repozitář.

Pro první nahrání použijte prázdný GitHub repozitář. Pokud již místní `.git`
existuje, první příkaz vynechte. Adresu vzdáleného repozitáře nahraďte vlastní:

```sh
git init -b main
git add .
git status --short
git commit -m "Initial CLI project"
git remote add origin https://github.com/mezerap/imapsync-docker.git
git push -u origin main
```

Před commitem má seznam obsahovat jen program a anonymní vzor, nikoli skutečné
účty, hesla, logy či lokální migrační záznamy. Pokud už `origin` existuje,
zkontrolujte `git remote -v` a nepřidávejte druhý stejný remote.


## Licence

Vlastní kód obalu (`migrate.py`, `migrate.sh`, `terminal_menu.py`), vlastní testy,
konfigurace a původní dokumentace tohoto projektu jsou pod [MIT licencí](LICENSE).

Převzatý `patches/IMAPClient.pm` **včetně místních úprav není přelicencován na MIT**.
Zůstává pod původními podmínkami Perlu: volba Artistic License nebo GNU GPL
verze 1 či novější podle původního oznámení. Viz [patches/LICENSE](patches/LICENSE)
a [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Python, Perl, imapsync a další součásti Docker image mají vlastní licenční
podmínky. MIT tohoto repozitáře se na ně nevztahuje. Projekt nevyžaduje externí
Python balíčky přes pip; používá standardní knihovnu.
