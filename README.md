# dsh-content

## Manifests

`manifest.<environment>.json` files are generated from the contents of the `/pages` directory.

The manifests are used as a structured index of page routes and their files, so applications can discover page content and related assets.

### Purpose

A manifest is a JSON file that describes:

- which directories are valid routes
- which files belong to each route
- the nested structure of files beneath each route
- which files apply to a given environment

Example output:

```json
{
	"route": "/research",
	"files": {
		"articles": {
			"ai-document-insights": {
				"article": "research/articles/ai-document-insights/article.json",
				"metadata": "research/articles/ai-document-insights/metadata.json"
			}
		}
	}
}
```

### Page Files

A directory is treated as a **route** only if it contains a file named `.page`.

This marker makes the directory the root of a page route.

For example:

```text
pages/
  research/
    .page
    articles/
      ai-document-insights/
        article.json
        metadata.json
```

Because `pages/research/.page` exists, `research` becomes a route and is emitted as:

```json
{
  "route": "/research",
  ...
}
```

Without a `.page` file, the directory is not treated as a route, even if it contains content.

#### Importance

The `.page` marker gives you an explicit way to say:

- “this folder should become a route”
- “everything underneath this folder belongs to that route”

This aims to avoid guessing based on folder names alone.

### Route Requirements

#### 1. A route requires `.page`

Only directories containing `.page` become route entries in the manifest.

#### 2. Folder structure is preserved under `files`

Everything beneath the route directory is represented as nested JSON objects.

#### 3. Parent directory names are preserved

Folder names are kept exactly as they appear, including hyphens.

Example:

```text
articles/long-form/
```

becomes:

```json
{
	"articles": {
		"long-form": {}
	}
}
```

#### 4. Leaf file keys are normalized

Leaf keys are derived from filenames by:

- removing the environment segment, if present
- removing the file extension
- converting the result to `camelCase`

Example:

- `article.json` → `article`
- `page-metadata.json` → `pageMetadata`
- `config.testing.json` → `config`

### Environments

The generator builds one manifest per environment.
Environments are defined in the `site.json`.

For example:

```json
{
	"environments": ["testing", "production"]
}
```

This generates:

- `manifest.testing.json`
- `manifest.production.json`

#### How to Declare Environment-Specific Files

A file is considered environment-specific when its name matches this pattern:

```text
<name>.<environment>.<extension>
```

Example:

- `config.testing.json`
- `config.production.json`

A file without an environment segment is treated as the default version and is included for all environments.

Example:

- `config.json`

#### Override behavior

For the same logical key path:

- the default file is used for all environments
- an environment-specific file overrides the default for that environment

Example directory:

```text
pages/
  research/
    .page
    config.json
    config.testing.json
    config.production.json
```

Generated behavior:

- `manifest.testing.json` uses `config.testing.json`
- `manifest.production.json` uses `config.production.json`

The manifest key remains the same:

```json
{
	"config": "..."
}
```

Only the selected file path changes by environment.

### Example Folder Layout

```text
pages/
  research/
    .page
    introduction.json
    introduction.testing.json
    articles/
      ai-document-insights/
        article.json
        metadata.json
```

#### Example result for `production`

```json
{
	"route": "/research",
	"files": {
		"intro": "research/intro.json",
		"articles": {
			"ai-document-insights": {
				"article": "research/articles/ai-document-insights/article.json",
				"metadata": "research/articles/ai-document-insights/metadata.json"
			}
		}
	}
}
```

#### Example result for `testing`

```json
{
	"route": "/research",
	"files": {
		"intro": "research/intro.testing.json",
		"articles": {
			"ai-document-insights": {
				"article": "research/articles/ai-document-insights/article.json",
				"metadata": "research/articles/ai-document-insights/metadata.json"
			}
		}
	}
}
```

Note that:

- `introduction.testing.json` overrides `introduction.json` only for `testing`
