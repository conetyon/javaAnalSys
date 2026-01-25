# Code Repositories Directory

This directory is for staging Java projects that you want to import into the system.

## Usage

1. **Copy Java projects** into subdirectories of this folder:
   ```
   code_repos/
   ├── spring-petclinic/
   │   └── src/main/java/...
   ├── my-java-project/
   │   └── src/...
   └── another-project/
       └── ...
   ```

2. **Import all projects** using the bulk import script:
   ```bash
   python scripts/batch_import/import_code_repos.py --all
   ```

3. **Import a single project**:
   ```bash
   python scripts/batch_import/import_code_repos.py --repo code_repos/spring-petclinic
   ```

## What Gets Imported

- The script recursively scans for `.java` files
- Parses each file using tree-sitter (Java AST)
- Extracts method-level code snippets
- Computes features (AST nodes, keywords, difficulty)
- Saves to database (idempotent via content hash)

## Excluded Directories

The following directories are automatically excluded:
- `target/` (Maven build output)
- `build/` (Gradle build output)
- `.git/` (version control)
- `node_modules/` (if mixed project)
- `test/` (optional, configurable)

## API Usage

You can also trigger imports via API (testable in Apifox):

```http
POST /api/bulk-import
Content-Type: application/json

{
  "repo_path": "code_repos/spring-petclinic"
}
```

Then poll for progress:
```http
GET /api/bulk-import/{job_id}
```

## Notes

- Imports are **idempotent**: Running the same import multiple times produces identical database state
- Failed file parsing does not stop the import (errors are logged)
- Progress is shown in console (CLI) or via API (for API imports)
