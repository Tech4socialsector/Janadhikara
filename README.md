# Janadhikara

**Community health worker application built with Frappe.**

Janadhikara gives community health teams a focused workspace for managing worker and partner information. It combines Frappe’s document, permissions, and data services with a responsive Vue application for day-to-day use.

## Highlights

- A responsive Vue 3 application served from `/janadhikara`.
- Frappe-backed records with user authentication and permissions.
- Configurable modules and DocType navigation, with visibility based on user roles.
- Worker and partner records, with additional DocTypes configurable in Frappe.
- Workspace announcements that can be targeted to users or roles.
- Search, filters, worklists, and mobile-friendly navigation.
- Progressive web app support, including a service worker and caching for previously loaded app pages and read requests.

## Technology

- [Frappe Framework](https://github.com/frappe/frappe) 16
- Python 3.14 or newer
- Vue 3, [frappe-ui](https://github.com/frappe/frappe-ui), and Tailwind CSS
- Vite for frontend development and production builds

## Requirements

- A Frappe bench using Frappe 16
- Python 3.14 or newer
- Node.js and Yarn for frontend development and builds

## Install

From your Frappe bench, fetch the repository and install the app on a site:

```bash
bench get-app <repository-url> --branch version-16
bench --site <site-name> install-app janadhikara
bench build
```

Then open `/janadhikara` on your site. Replace `<repository-url>` and `<site-name>` with your repository and Frappe site values.

## Configure your workspace

After installation, sign in with an administrator account and configure the workspace in Frappe:

1. Set the app name, logo, and other branding in **App Setting**.
2. Add the modules and DocTypes users should see in **App Module Setting**. Module visibility can be restricted by role.
3. Create announcements in **Announcement** and choose whether they apply to everyone, selected roles, or selected users.

## Frontend development

Run the bench from one terminal:

```bash
bench start
```

In a second terminal, install the frontend dependencies and start Vite:

```bash
cd frontend
yarn install
yarn dev
```

Create production assets with:

```bash
yarn build
```

The build writes the compiled frontend assets into the Frappe app and updates its page shell. Serve the app through the bench at `/janadhikara`.

## Project layout

```text
.
├── frontend/                 # Vue application and Vite configuration
└── janadhikara/
    ├── api.py                # Whitelisted Frappe endpoints
    ├── app_config/           # App settings, modules, announcements, AI guide
    ├── engine/               # Operational DocTypes, including Employee
    ├── masters/              # Master data DocTypes
    ├── common/               # Shared DocTypes and behavior
    ├── hooks.py              # Frappe hooks and /janadhikara route
    └── www/                  # Frappe page shell for the Vue app
```

## Tests and code quality

Run the app’s Python tests on an installed development site:

```bash
bench --site <site-name> run-tests --app janadhikara
```

Install the repository’s pre-commit hooks before contributing:

```bash
pre-commit install
```

The configured checks include Ruff, ESLint, Prettier, and pyupgrade. GitHub Actions also runs the server test suite and configured security/lint checks.

## Contributing

Issues and pull requests are welcome. Please describe the user-facing change, include steps to reproduce or review it, and update documentation when behavior or setup changes.

## License

Janadhikara is released under the [MIT License](license.txt).
