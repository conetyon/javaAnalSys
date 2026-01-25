# Database Initialization Fixes

**Date**: 2026-01-24
**Issue**: Data initialization scripts failing with cursor errors and missing data

## Problems Identified

### 1. MySQLClient Context Manager Usage
**Issue**: Scripts used `conn.cursor()` when `conn` is a MySQLClient object, not a raw connection.

**Root Cause**: When using `with MySQLClient() as conn:`, the `conn` variable is the MySQLClient instance itself, not the underlying MySQL connection object.

**Solution**: Access the underlying connection via `conn._conn.cursor()`.

### 2. Transaction Commit Issues
**Issue**: Data was inserted but not visible in database (showed 0 records).

**Root Cause**: MySQLClient with `autocommit=True` (default) doesn't explicitly commit when using context manager. The context manager only commits when `autocommit=False`.

**Solution**: Changed all initialization scripts to use `autocommit=False`:
```python
client = MySQLClient(db=DB_NAME, autocommit=False)
```

### 3. Knowledge Points Parsing Failed
**Issue**: `parse_kp_dml_file()` returned 0 statements despite kp_dml.sql having data.

**Root Cause**: Regex pattern didn't support `ON DUPLICATE KEY UPDATE` syntax used in kp_dml.sql.

**Original Pattern**:
```python
r'INSERT\s+INTO\s+knowledge_points\s*\([^)]+\)\s*VALUES\s*\([^;]+\);'
```

**Fixed Pattern**:
```python
r'INSERT\s+INTO\s+knowledge_points\s*\([^)]+\)\s*VALUES\s+.+?;'
```

### 4. REPLACE INTO Syntax Conflict
**Issue**: Converting `INSERT ... ON DUPLICATE KEY UPDATE` to `REPLACE INTO` caused syntax errors.

**Root Cause**: `REPLACE INTO` doesn't support `ON DUPLICATE KEY UPDATE` clause.

**Solution**: Modified `convert_insert_to_replace()` to skip conversion for statements already using `ON DUPLICATE KEY UPDATE`:
```python
def convert_insert_to_replace(insert_stmt: str) -> str:
    # If statement already uses ON DUPLICATE KEY UPDATE, it's idempotent
    if re.search(r'ON\s+DUPLICATE\s+KEY\s+UPDATE', insert_stmt, re.IGNORECASE):
        return insert_stmt
    # Otherwise, convert to REPLACE
    return re.sub(r'^\s*INSERT\s+INTO', 'REPLACE INTO', insert_stmt, flags=re.IGNORECASE)
```

### 5. Missing Print Statements
**Issue**: Scripts ran silently, making debugging difficult on Windows (encoding issues with log files).

**Solution**: Added print() statements alongside logger calls for immediate console feedback.

## Files Modified

1. **scripts/init_data/init_schema.py**
   - Added `conn._conn.cursor()` instead of `conn.cursor()`
   - Added detailed print statements for each migration step
   - Improved comment filtering in SQL parsing

2. **scripts/init_data/load_knowledge_points.py**
   - Changed to `autocommit=False`
   - Fixed `convert_insert_to_replace()` to handle ON DUPLICATE KEY UPDATE
   - Updated regex pattern in `parse_kp_dml_file()`
   - Added print statements for progress tracking
   - Fixed cursor usage to `conn._conn.cursor()`

3. **scripts/init_data/analyze_sample_code.py**
   - Changed to `autocommit=False`
   - Fixed cursor usage to `conn._conn.cursor()`
   - Added detailed print statements
   - Fixed column name: `filepath` instead of `file_path`

4. **scripts/init_data/check_status.py**
   - Added database connection test using `fetch_one()`
   - Fixed cursor usage to `conn._conn.cursor()`
   - Updated required tables list to include `experiment_runs` and `bulk_import_jobs`

## Testing Results

### Before Fixes
```
[FAIL] Step failed with exit code 1
[FAIL] Knowledge points: FAIL (0 records)
[FAIL] Code snippets: FAIL (0 snippets)
[FAIL] Code files: FAIL (0 files)
```

### After Fixes
```
[OK] ALL INITIALIZATION COMPLETE

Database Status:
  [OK] Database connection: PASS
  [OK] Tables exist: PASS (5 tables)
  [OK] Knowledge points: PASS (147 records)
  [OK] Code snippets: PASS (30 snippets)
  [OK] Code files: PASS (1 files)

[OK] Database is ready
```

## Lessons Learned

1. **Context Manager Behavior**: When wrapping database clients, document whether the context manager returns the wrapper or the underlying connection.

2. **Autocommit vs Explicit Commit**: For initialization scripts, explicit commits (`autocommit=False`) are safer than relying on autocommit behavior.

3. **Regex Patterns for SQL**: When parsing SQL with regex, use non-greedy quantifiers (`.+?`) to avoid matching too much.

4. **Idempotency Strategies**: Don't blindly convert SQL - check if it's already idempotent (e.g., ON DUPLICATE KEY UPDATE).

5. **Debugging on Windows**: Print statements are more reliable than log files for immediate feedback due to encoding issues.

## Verification Commands

```bash
# Run complete initialization
python scripts/init_data/run_all.py

# Check database status
python scripts/init_data/check_status.py

# Test individual steps
python scripts/init_data/init_schema.py
python scripts/init_data/load_knowledge_points.py
python scripts/init_data/analyze_sample_code.py
```

## Exit Codes

- `0`: Success
- `1`: Failure

All scripts now properly return exit codes that can be checked by the orchestrator (`run_all.py`).
