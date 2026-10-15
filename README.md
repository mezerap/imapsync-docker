# Imapsync CLI

Migrate IMAP mailboxes locally with Docker, a JSON configuration, and an
interactive terminal wizard. Select multiple accounts, check credentials,
inspect folder sizes, run a simulation, create folders, or transfer messages.
This project provides a CLI only.

## Requirements

- macOS, Bash, Git, and Python 3.9 or later. This project has been tested on
  macOS and uses the Unix `fcntl` and `curses` modules. Native Windows is not
  supported.
- A running [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/)
  installation with Docker Compose. If needed, install Python from
  [python.org](https://www.python.org/downloads/macos/).
- Existing source and destination mailboxes accessible over direct SSL/TLS,
  usually on port 993. This wrapper does not implement STARTTLS or OAuth.

No pip packages are required. The Bash launcher starts Python, while imapsync
runs in a disposable container. The image uses AMD64; on Apple Silicon,
Docker Desktop runs it using its AMD64 support.

## Install from GitHub on a new computer

```sh
mkdir -p ~/local-docker
cd ~/local-docker
git clone https://github.com/mezerap/imapsync-docker.git imapsync-migration
cd imapsync-migration
```

Start Docker Desktop and check the required tools:

```sh
python3 --version
git --version
docker compose version
docker info
```

In the **freshly cloned** directory, create your local configuration and prepare
the data directories:

```sh
cp accounts.example.json accounts.json
mkdir -p passwords logs
chmod 700 passwords logs
chmod 600 accounts.json
chmod +x migrate.sh migrate.py
docker compose pull imapsync
./migrate.sh --help
```

Do not repeat the `cp` command over an existing, configured `accounts.json`:
it would overwrite your accounts. Real accounts, passwords, and logs are
excluded from GitHub. On a new computer, enter them yourself or restore them
from your private backup.

## Add a mailbox

Edit the anonymous template in `accounts.json`. For example:

```json
[
  {
    "id": "first-mailbox",
    "enabled": false,
    "source": {
      "host": "imap.old.example.com",
      "port": 993,
      "user": "mailbox@example.com",
      "password_file": "first-source.txt"
    },
    "target": {
      "host": "imap.new.example.com",
      "port": 993,
      "user": "mailbox@example.com",
      "password_file": "first-target.txt"
    },
    "automap": false,
    "addheader": true,
    "folder_map": {}
  }
]
```

Replace the servers and usernames with the real values. Create
`passwords/first-source.txt` and `passwords/first-target.txt`. Put only the
corresponding password on the first line of each file, without quotes or notes.

```sh
chmod 600 passwords/first-source.txt passwords/first-target.txt
```

Keep passwords out of JSON and command-line arguments. To add another mailbox,
append another object to the same JSON array, separated by a comma, with a
unique `id` and its own password files. It will appear the next time you start
the wizard.

### Configuration fields

| Field | Meaning |
| --- | --- |
| `id` | Unique account name: 1–64 letters, digits, underscores, or hyphens. The first character must be a letter or digit. |
| `enabled` | Includes the account in `--all`. A disabled account can still be selected manually for a single run. Defaults to `false`. |
| `source`, `target` | Source/destination server (`host`), username (`user`), port (defaults to `993`), and `password_file`. |
| `password_file` | A filename inside `passwords/`, without a directory path. |
| `automap` | Automatically estimates mappings for special folders. Defaults to `false`. |
| `folder_map` | Exact source → destination mappings; these take precedence over automatic mapping. Defaults to `{}`. |
| `separator2` | Optional single-character hierarchy separator used by the destination server, such as a dot or vertical bar. Use the value required by that server. |
| `addheader` | Adds an identifying header when transferring messages that lack one. Defaults to `false` when omitted; the template sets it to `true`. |

JSON does not support comments. Unknown fields are rejected. The configuration
does not accept arbitrary additional imapsync switches.

### Explicit folder mappings

This example maps several folder name variants into a flat destination
structure:

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

Place this fragment inside the relevant account object. Check the folder names
on both servers before using it: this is an example, not a universal profile.
It merges several source folders into a single destination folder, including
a yearly Trash subfolder. For automatic mapping, use `automap: true` and always
review the result in a dry run.

## Interactive terminal wizard

```sh
./migrate.sh
```

- **↑/↓** or **j/k**: move between items.
- **Space**: select or deselect an account; multiple accounts can be selected.
- **a**: select or deselect all accounts.
- **Enter**: confirm; if no accounts are selected, choose the highlighted account.
- **q**, **Esc**, or **Ctrl+C**: exit.

After choosing accounts, select a mode and review the summary, including folder
mappings. The default mode is a dry run. For modes that make real changes,
the final confirmation defaults to **Cancel**. The wizard does not modify
`accounts.json` or password files. A numbered menu is used when the terminal
lacks a suitable `TERM`; outside an interactive terminal, use direct arguments.
Running `python3 migrate.py` opens the same menus. The current terminal prompts
are in Czech.

| Mode | Imapsync switches | Behavior |
| --- | --- | --- |
| `check` | `--justlogin` | Check credentials only. |
| `sizes` | `--justfoldersizes` | Report folders, message counts, and sizes. |
| `dry-run` | `--dry` | Compare and simulate without transferring messages. |
| `folders-dry-run` | `--justfolders --dry` | Preview folder mapping and creation without changes. |
| `folders` | `--justfolders` | Create folders without transferring messages. |
| `sync` | No restriction from these switches | Transfer messages. |
| `plan` | Does not execute the command | Print the command without running Docker or connecting to servers. |

For your first mailbox, run **check → dry-run → sync**, followed by another
dry run. Messages already transferred should be skipped on subsequent runs.
A dry run cannot fully simulate the contents of a destination folder that does
not exist yet; creating that folder is a real change.

## Direct commands and multiple accounts

The launcher passes its arguments to Python. For example:

```sh
./migrate.sh --account first-mailbox --mode check
./migrate.sh --account first-mailbox --mode sizes
./migrate.sh --account first-mailbox --mode dry-run
./migrate.sh --account first-mailbox --mode folders-dry-run
./migrate.sh --all --mode dry-run
```

To intentionally run modes that make changes:

```sh
./migrate.sh --account first-mailbox --mode folders
./migrate.sh --account first-mailbox --mode sync
```

**Direct commands do not ask for confirmation.** When selecting accounts via
arguments without `--mode`, the default is `plan`. `--all` includes only
accounts with `enabled: true`. Manual selection in the wizard and `--account`
can select an account for a single run even when it is disabled.

Use the ignored `configs/` directory for separate local configurations:

```sh
./migrate.sh --config configs/client.json
./migrate.sh --config configs/client.json --account first-mailbox --mode plan
```

Relative `--config` paths are resolved from the current working directory.
Passwords and logs always remain in `passwords/` and `logs/` next to the program.

## Logs, repeat runs, and limitations

Output includes individual transfers and skipped messages, IDs, sizes, speed,
errors, and final statistics. Each run saves a log under `logs/`, with the
account ID, mode, and UTC timestamp in its filename. Logs can contain private
metadata; debugging modes may expose additional details. Password files are
mounted read-only into the container.

Keep folder mappings and message identification settings consistent across
repeat runs. Imapsync compares Message-Id/Received headers and normally skips
messages already present. The wrapper always adds `--nosyncduplicates`. It does
not enable message or folder deletion; it may synchronize message flags.
Trash and Spam folders are subject to the provider's retention policies.

The complete account selection is validated before the first connection.
Accounts run sequentially, and the batch stops at the first error.
`.migration.lock` prevents simultaneous jobs started by this script in the same
project; it does not cover other project copies or manual Docker commands.
Keep the terminal open, Docker running, and the computer awake. A closed client
does not confirm that a transfer has finished; check logs and containers before
starting another run.

## Update and reuse

When no job is running, update the code:

```sh
git pull --ff-only
docker compose pull imapsync
```

Ignored local accounts, passwords, and logs remain outside Git. If Git reports
local code changes, resolve them first; do not use `reset --hard` for updates.

The image is pinned to a tested digest of version 2.326. `pull` downloads the
version specified in Compose; **it does not automatically upgrade to the latest
imapsync**. Changing the digest requires checking compatibility with
`patches/IMAPClient.pm` and running the tests. Do not blindly replace it with
`latest`. The patched library preserves APPEND byte lengths with Unicode input
and prevents blind retries of writes after an uncertain response. Its origin
and terms are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Containers use `--rm` and are removed after each run; the image remains.
Project data uses bind mounts: `docker compose down -v` does not remove local
passwords or logs. Deleting the entire project directory also deletes local
data and recovery backups; this is not part of a normal update.

## Verify without connecting to mailboxes

```sh
./migrate.sh --help
docker compose config --quiet
python3 -B -m unittest discover -s tests -p 'test_*.py'
```

Tests cover menus, multiple accounts, modes, safe cancellation, and the
concurrency lock. Run the APPEND byte-length regression tests with synthetic
data inside the container:

```sh
docker compose run --rm -T --entrypoint perl \
  --volume "$PWD/tests:/tests:ro" imapsync /tests/append-octets.t
```

None of these checks logs into mailboxes or migrates messages.

## What belongs on GitHub

Track the program, Compose file, anonymous template, tests, documentation, and
required library patch. `.gitignore` excludes real `accounts*.json` files,
`configs/`, passwords, logs including `logs/recovery/`, local `MIGRATION.md`,
the agent handoff file, environment files, and temporary files. Exceptions are
`accounts.example.json` and empty `.gitkeep` files in the data directories,
so those directories are created when cloning.

`.gitignore` does not remove files already committed to Git history. Do not
add real data using `git add -f` or include it in examples or the README.
Keep private backups of ignored files outside the repository if needed.

To publish a separate copy, first create an empty GitHub repository. Skip
`git init` if the local `.git` directory already exists, and replace the remote
URL below with your own repository URL:

```sh
git init -b main
git add .
git status --short
git commit -m "Initial CLI project"
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY.git
git push -u origin main
```

Before committing, make sure the file list contains only the program and
anonymous examples, without real accounts, passwords, logs, or local migration
reports. If `origin` already exists, check `git remote -v` and update that remote
instead of adding it again.

## License

The wrapper code (`migrate.py`, `migrate.sh`, `terminal_menu.py`), original tests,
configuration, and original project documentation are covered by the
[MIT License](LICENSE).

The third-party `patches/IMAPClient.pm`, **including local modifications, is not
relicensed under MIT**. It retains its original Perl terms: a choice of the
Artistic License or GNU GPL version 1 or later, as stated in its original notice.
See [patches/LICENSE](patches/LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Python, Perl, imapsync, and other components in the Docker image have their own
license terms. This repository's MIT License does not apply to them. The
project uses Python's standard library and requires no external pip packages.
