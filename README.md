### Hexlet tests and linter status:

[![Actions Status](https://github.com/Alex-tolch/devops-engineer-from-scratch-project-315/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/Alex-tolch/devops-engineer-from-scratch-project-315/actions)

### Ansible layout

| Playbook | Purpose |
|----------|---------|
| `playbook.yml` | Docker host + UFW (`roles/docker_host`, `roles/ufw`) |
| `deploy.yml` | Application stack (`roles/app_deploy`, includes `roles/nginx_app`) |

Inventory: `hosts`. Target hosts should run **Ubuntu** or **Debian** (e.g. **Google Compute Engine**).

### Galaxy dependencies

Install collections and roles from `requirements.yml`:

```bash
ansible-galaxy install -r requirements.yml
```

Galaxy roles used:

- **geerlingguy.docker** — Docker CE (via `roles/docker_host`)
- **geerlingguy.nginx** — Nginx package and service (via `roles/nginx_app`)
- **geerlingguy.certbot** — Certbot install and renewal timer (via `roles/nginx_app`)
- **jfx.system.ufw** — host firewall (via `roles/ufw`)

Collections: **community.general**, **community.docker**, **jfx.system**.

### Provision (Docker + firewall)

```bash
make provision PRIVATE_KEY=~/.ssh/your_key
```

Or:

```bash
ansible-playbook -i hosts playbook.yml --private-key /path/to/private_key
```

Re-running is idempotent. UFW allows inbound **22**, **80**, **443**; default incoming policy is **deny**.

**Python on the target host:** `deploy.yml` runs `community.docker` modules on the VM (not on the Ansible controller). The collection docs state that the [Docker SDK for Python must be installed on the machines where those modules execute](https://docs.ansible.com/ansible/latest/collections/community/docker/docsite/scenario_guide.html#requirements). `make provision` installs **`python3-docker`** on the VM via `roles/docker_host` so `make deploy` can manage containers.

**Google Cloud VPC firewall:** allow SSH (your IP or IAP), HTTP/HTTPS for a public app. Do **not** expose PostgreSQL **5432** to `0.0.0.0/0`.

### Public URL

- Application: [https://project-devops.ddns.net/](https://project-devops.ddns.net/)
- DDNS hostname should match the VM in `hosts`. Update the record if the VM public IP changes.

### Deploy (application)

1. Install Galaxy deps: `ansible-galaxy install -r requirements.yml`
2. **Secrets:** copy `group_vars/all/vault.yml.example` → `group_vars/all/vault.yml`, set **`postgres_password`** (and registry / S3 vars as needed), then `ansible-vault encrypt group_vars/all/vault.yml`. Plaintext `vault.yml` is gitignored; you may commit the **encrypted** file.
3. Adjust `group_vars/all/main.yml` (image tag, TLS domain, etc.) or role defaults under `roles/app_deploy/defaults/main.yml`.
4. Deploy:

```bash
make deploy PRIVATE_KEY=~/.ssh/your_key
```

(`Makefile` uses `--vault-password-file` when `VAULT_PASSWORD_FILE` is set, default `~/.vault.pass`.)

Or:

```bash
ansible-playbook -i hosts deploy.yml --private-key /path/to/key --ask-vault-pass
```

**Updates:** the role pulls the image and recreates the app container when the image or config changes.

**Rollback:** pin a stable tag in `group_vars/all/main.yml`, e.g. `app_image_tag: v1.2.3`, then deploy again. The play can fall back to **`app_rollback_image`** if the primary image task fails.

**Data / logs:** `app_data_dir` and `app_logs_dir` are bind-mounted into the app; **`postgres_data_dir`** persists the database.

### Nginx reverse proxy (`roles/nginx_app`)

When **`app_nginx_enabled`** is true (default), deploy configures **Nginx** on the VM:

- Listens on **80** / **443** (HTTPS when **`app_tls_enabled`** is true).
- Proxies to the app at **`127.0.0.1:8080`** (Docker publishes the app port on loopback only).
- **`proxy_cache`** for static-like assets (`*.js`, `*.css`, images, fonts, etc.).
- **`/uploads/`** served from **`app_data_dir/uploads`** on the host.

Set **`app_nginx_enabled: false`** if you need the app bound to `:80` directly.

TLS variables (defaults in `roles/nginx_app/defaults/main.yml`, overrides in `group_vars/all/main.yml`):

- **`app_tls_enabled`**, **`app_tls_domain`**, optional **`app_tls_email`**
- On **Ubuntu**, the role adds the **Certbot PPA** and installs the **latest** `certbot` (avoids a Python 3.11+ bug that masks CA errors as `AttributeError: can't set attribute`).
- If issuance fails, check **`/var/log/letsencrypt/letsencrypt.log`** on the VM.

### S3 / GCS (manual steps)

- **GCS bucket** — create a bucket (name matches `STORAGE_S3_BUCKET` in Vault).
- **S3 interoperability (HMAC)** — _Cloud Storage → Settings → Interoperability_ — create HMAC keys; store as `STORAGE_S3_ACCESSKEY` / `STORAGE_S3_SECRETKEY` in Vault.
- **IAM** — grant the service account object access to the bucket.
- **Vault env vars** — `STORAGE_S3_ENDPOINT` (`https://storage.googleapis.com`), `STORAGE_S3_REGION` (often `us-east-1` for SigV4 with GCS).
- **Exposure** — VM firewall 80/443 only; bucket not world-writable; app uses Vault credentials only.

### Spring Boot environment

The app uses **`SPRING_PROFILES_ACTIVE=prod`**. Ansible sets **`SPRING_DATASOURCE_*`** for bundled Postgres. For S3-compatible storage, set **`STORAGE_S3_*`** under **`app_env_secrets`** in Vault — see **`group_vars/all/vault.yml.example`**.
