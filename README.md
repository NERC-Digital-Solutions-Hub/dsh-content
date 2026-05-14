# dsh-content

## Manifests

`manifest.<environment>.json` files are generated from the contents of the `/pages` directory.

The manifests act as a structured index of page routes and their content assets, so applications can discover and retrieve page content at build time without hardcoding repository paths.

A manifest is intended to be a machine-readable contract between the content repository and consuming applications.

## Manifest Structure

Each manifest contains:

- the manifest schema version
- the content version / generation timestamp
- the environment the manifest was generated for
- a `pages` object keyed by stable page IDs
- one route per page
- an `assets` object for each page
- asset descriptors containing the file `path` and asset `type`

Example:

```json
{
	"schemaVersion": 1,
	"version": "2026-05-08T10:47:25Z",
	"generatedAt": "2026-05-08T10:47:25Z",
	"environment": "development",
	"pages": {
		"research": {
			"route": "/research",
			"assets": {
				"main": {
					"path": "research/main.md",
					"type": "markdown"
				},
				"articles.ai-document-insights.article": {
					"path": "research/articles/ai-document-insights/article.md",
					"type": "markdown"
				},
				"articles.ai-document-insights.metadata": {
					"path": "research/articles/ai-document-insights/metadata.json",
					"type": "json"
				}
			}
		}
	}
}
```

## Purpose

A manifest describes:

- which directories are valid page routes
- the stable ID for each page
- which assets belong to each page
- the route associated with each page
- the content path for each asset
- the type of each asset
- which files apply to a given environment

Applications should use the manifest to request content semantically, for example:

```ts
const page = source.page('research');
const main = await page.asset('main').text();
const metadata = await page.asset('articles.ai-document-insights.metadata').json();
```

This keeps consuming applications independent from the physical folder layout of the content repository.

## Page Files

A directory is treated as a page route only if it contains a file named `.page`.

This marker makes the directory the root of a page route.

For example:

```text
pages/
  research/
    .page
    main.md
    articles/
      ai-document-insights/
        article.md
        metadata.json
```

Because `pages/research/.page` exists, `research` becomes a page route and is emitted as:

```json
{
	"pages": {
		"research": {
			"route": "/research",
			"assets": {
				"main": {
					"path": "research/main.md",
					"type": "markdown"
				},
				"articles.ai-document-insights.article": {
					"path": "research/articles/ai-document-insights/article.md",
					"type": "markdown"
				},
				"articles.ai-document-insights.metadata": {
					"path": "research/articles/ai-document-insights/metadata.json",
					"type": "json"
				}
			}
		}
	}
}
```

Without a `.page` file, the directory is not treated as a route, even if it contains content.

### `.page` Metadata

The `.page` file may be empty, or it may contain JSON metadata.

Use this when you want to provide a stable page ID explicitly:

```json
{
	"id": "uprn-service"
}
```

This is useful when the route path and the page ID should not be tightly coupled.

For example:

```text
pages/
  apps/
    uprn-service/
      .page
      introduction.md
      settings.json
```

With this `.page` file:

```json
{
	"id": "uprn-service"
}
```

The manifest page entry is keyed by `uprn-service`:

```json
{
	"pages": {
		"uprn-service": {
			"route": "/apps/uprn-service",
			"assets": {
				"introduction": {
					"path": "apps/uprn-service/introduction.md",
					"type": "markdown"
				},
				"settings": {
					"path": "apps/uprn-service/settings.json",
					"type": "json"
				}
			}
		}
	}
}
```

## Page IDs

The `pages` object is keyed by page ID.

Example:

```json
{
	"pages": {
		"home": {},
		"research": {},
		"uprn-service": {}
	}
}
```

If the `.page` file contains an explicit `id`, that value is used.

If no ID is provided, the generator derives one from the route:

| Route                | Default page ID |
| -------------------- | --------------- |
| `/`                  | `home`          |
| `/research`          | `research`      |
| `/apps/uprn-service` | `uprn-service`  |

If two routes would produce the same page ID, add explicit IDs to their `.page` files.

## Assets

Each page contains an `assets` object.

An asset entry maps a stable asset key to an asset descriptor:

```json
{
	"assets": {
		"introduction": {
			"path": "apps/uprn-service/introduction.md",
			"type": "markdown"
		}
	}
}
```

### Asset Descriptor

Each asset descriptor contains:

| Field  | Description                                       |
| ------ | ------------------------------------------------- |
| `path` | File path relative to the `/pages` directory      |
| `type` | Inferred content type based on the file extension |

Example:

```json
{
	"path": "research/main.md",
	"type": "markdown"
}
```

### Asset Types

Asset types are inferred from file extensions.

Common examples:

| Extension       | Type       |
| --------------- | ---------- |
| `.md`           | `markdown` |
| `.mdx`          | `markdown` |
| `.json`         | `json`     |
| `.csv`          | `csv`      |
| `.svg`          | `svg`      |
| `.png`          | `png`      |
| `.jpg`, `.jpeg` | `jpg`      |
| `.webp`         | `webp`     |
| `.xlsx`         | `xlsx`     |
| `.txt`          | `text`     |
| `.pdf`          | `pdf`      |

Unknown extensions are emitted as their extension name. Files without an extension are emitted as `binary`.

## Asset Keys

Asset keys are stable lookup keys used by consuming applications.

Asset keys are derived from the file path beneath the page route directory by:

1. removing the environment segment, if present
2. removing the file extension
3. joining folder names and the filename with `.`
4. preserving path-style names such as kebab-case

Examples:

| File path beneath route directory                                     | Asset key                                                         |
| --------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `introduction.md`                                                     | `introduction`                                                    |
| `settings.production.json`                                            | `settings`                                                        |
| `svgs/bootstrap/info-circle.svg`                                      | `svgs.bootstrap.info-circle`                                      |
| `generated/csv/config/datasets.csv`                                   | `generated.csv.config.datasets`                                   |
| `articles/ai-document-insights/metadata.json`                         | `articles.ai-document-insights.metadata`                          |
| `articles/ai-document-insights/architecture-extract-descriptions.svg` | `articles.ai-document-insights.architecture-extract-descriptions` |

The manifest does not convert filenames to camelCase. This keeps keys consistent with content paths and avoids mixed styles such as:

```text
ai-document-insights.architectureExtractDescriptions
```

Prefer:

```text
ai-document-insights.architecture-extract-descriptions
```

## Route Requirements

### 1. A route requires `.page`

Only directories containing `.page` become page entries in the manifest.

### 2. Nested route directories are excluded from parent routes

If a directory inside a route also contains `.page`, it becomes its own route. Its files are not included in the parent route's assets.

Example:

```text
pages/
  research/
    .page
    main.md
    articles/
      .page
      index.md
```

This produces separate page entries for:

```text
/research
/research/articles
```

### 3. Asset keys are flat

Older manifests used a nested `files` object.

New manifests use a flat `assets` object.

Old shape:

```json
{
	"files": {
		"articles": {
			"ai-document-insights": {
				"metadata": "research/articles/ai-document-insights/metadata.json"
			}
		}
	}
}
```

New shape:

```json
{
	"assets": {
		"articles.ai-document-insights.metadata": {
			"path": "research/articles/ai-document-insights/metadata.json",
			"type": "json"
		}
	}
}
```

### 4. Asset values are descriptors

Older manifests mapped keys directly to file paths.

Old shape:

```json
{
	"settings": "apps/uprn-service/settings.json"
}
```

New shape:

```json
{
	"settings": {
		"path": "apps/uprn-service/settings.json",
		"type": "json"
	}
}
```

## Environments

The generator builds one manifest per environment.

Environments are defined in `site.json`.

For example:

```json
{
	"environments": ["testing", "production"]
}
```

This generates:

- `manifest.testing.json`
- `manifest.production.json`

If `environments` is not present, the generator falls back to `currentenvironment`:

```json
{
	"currentenvironment": "development"
}
```

This generates:

- `manifest.development.json`

## Environment-Specific Files

A file is considered environment-specific when its name matches this pattern:

```text
<name>.<environment>.<extension>
```

Examples:

```text
settings.testing.json
settings.production.json
introduction.development.md
```

A file without an environment segment is treated as the default version and is included for all environments.

Example:

```text
settings.json
```

## Override Behaviour

For the same asset key:

- the default file is used for all environments
- an environment-specific file overrides the default for that environment

Example directory:

```text
pages/
  research/
    .page
    settings.json
    settings.testing.json
    settings.production.json
```

Generated behaviour:

- `manifest.testing.json` uses `settings.testing.json`
- `manifest.production.json` uses `settings.production.json`
- other environments use `settings.json`, if generated

The asset key remains the same:

```json
{
	"settings": {
		"path": "research/settings.production.json",
		"type": "json"
	}
}
```

Only the selected file path changes by environment.

## Example Folder Layout

```text
pages/
  research/
    .page
    main.md
    main.testing.md
    articles/
      ai-document-insights/
        article.md
        metadata.json
        architecture-extract-descriptions.svg
```

## Example Result for `production`

```json
{
	"schemaVersion": 1,
	"version": "2026-05-08T10:47:25Z",
	"generatedAt": "2026-05-08T10:47:25Z",
	"environment": "production",
	"pages": {
		"research": {
			"route": "/research",
			"assets": {
				"main": {
					"path": "research/main.md",
					"type": "markdown"
				},
				"articles.ai-document-insights.article": {
					"path": "research/articles/ai-document-insights/article.md",
					"type": "markdown"
				},
				"articles.ai-document-insights.metadata": {
					"path": "research/articles/ai-document-insights/metadata.json",
					"type": "json"
				},
				"articles.ai-document-insights.architecture-extract-descriptions": {
					"path": "research/articles/ai-document-insights/architecture-extract-descriptions.svg",
					"type": "svg"
				}
			}
		}
	}
}
```

## Example Result for `testing`

```json
{
	"schemaVersion": 1,
	"version": "2026-05-08T10:47:25Z",
	"generatedAt": "2026-05-08T10:47:25Z",
	"environment": "testing",
	"pages": {
		"research": {
			"route": "/research",
			"assets": {
				"main": {
					"path": "research/main.testing.md",
					"type": "markdown"
				},
				"articles.ai-document-insights.article": {
					"path": "research/articles/ai-document-insights/article.md",
					"type": "markdown"
				},
				"articles.ai-document-insights.metadata": {
					"path": "research/articles/ai-document-insights/metadata.json",
					"type": "json"
				},
				"articles.ai-document-insights.architecture-extract-descriptions": {
					"path": "research/articles/ai-document-insights/architecture-extract-descriptions.svg",
					"type": "svg"
				}
			}
		}
	}
}
```

Note that:

- `main.testing.md` overrides `main.md` only for `testing`
- the asset key stays as `main`
- the asset descriptor changes by environment

## Example UPRN Page

Example folder layout:

```text
pages/
  apps/
    uprn-service/
      .page
      introduction.development.md
      settings.development.json
      climatejust-renderers.json
      generated/
        csv/
          config/
            datasets.csv
            domains.csv
            folders.csv
            variables.csv
        manifest.json
```

Example `.page` file:

```json
{
	"id": "uprn-service"
}
```

Example manifest output:

```json
{
	"schemaVersion": 1,
	"version": "2026-05-08T10:47:25Z",
	"generatedAt": "2026-05-08T10:47:25Z",
	"environment": "development",
	"pages": {
		"uprn-service": {
			"route": "/apps/uprn-service",
			"assets": {
				"climatejust-renderers": {
					"path": "apps/uprn-service/climatejust-renderers.json",
					"type": "json"
				},
				"generated.csv.config.datasets": {
					"path": "apps/uprn-service/generated/csv/config/datasets.csv",
					"type": "csv"
				},
				"generated.csv.config.domains": {
					"path": "apps/uprn-service/generated/csv/config/domains.csv",
					"type": "csv"
				},
				"generated.csv.config.folders": {
					"path": "apps/uprn-service/generated/csv/config/folders.csv",
					"type": "csv"
				},
				"generated.csv.config.variables": {
					"path": "apps/uprn-service/generated/csv/config/variables.csv",
					"type": "csv"
				},
				"generated.manifest": {
					"path": "apps/uprn-service/generated/manifest.json",
					"type": "json"
				},
				"introduction": {
					"path": "apps/uprn-service/introduction.development.md",
					"type": "markdown"
				},
				"settings": {
					"path": "apps/uprn-service/settings.development.json",
					"type": "json"
				}
			}
		}
	}
}
```

## Consuming the Manifest

A consuming application should treat the manifest as the source of truth for content locations.

Instead of hardcoding paths such as:

```ts
const url = `${baseUrl}/apps/uprn-service/settings.production.json`;
```

use the manifest:

```ts
const page = source.page('uprn-service');
const settings = await page.asset('settings').json();
```

For build-time content retrieval in SvelteKit, use the content source from server-side load code and prerender the route:

```ts
import type { PageServerLoad } from './$types';
import { createContentSource } from '$lib/server/content-source';

export const prerender = true;

export const load: PageServerLoad = async ({ fetch }) => {
	const source = await createContentSource({ fetch });
	const page = source.page('uprn-service');

	return {
		introduction: await page.asset('introduction').text(),
		settings: await page.asset('settings').json(),
	};
};
```

This allows the content repository layout to change without requiring application code to be refactored, as long as page IDs and asset keys remain stable.
