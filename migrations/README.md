# Database Migrations

This directory contains database migrations managed by [Alembic](https://alembic.sqlalchemy.org/).

## Setup

1. Install dependencies:
   ```bash
   pip install alembic sqlalchemy psycopg2-binary
   ```

2. Configure database URL (choose one):
   ```bash
   # Option 1: Set environment variable
   export DATABASE_URL=postgresql://user:password@localhost:5432/n8n

   # Option 2: Edit alembic.ini
   sqlalchemy.url = postgresql://user:password@localhost:5432/n8n
   ```

## Commands

### Check Current Version
```bash
alembic current
```

### View Migration History
```bash
alembic history
```

### Upgrade Database
```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade 001
```

### Downgrade Database
```bash
# Downgrade one revision
alembic downgrade -1

# Downgrade to base (remove all)
alembic downgrade base
```

### Create New Migration

#### Auto-generate from model changes
```bash
alembic revision --autogenerate -m "description of changes"
```

#### Create empty migration
```bash
alembic revision -m "description of changes"
```

## Migration Files

| Revision | Description |
|----------|-------------|
| 001 | Initial database schema |

## Schema Overview

### `judicial` Schema
- `cases` - Judicial cases
- `documents` - Uploaded documents
- `firac_analyses` - FIRAC legal analyses
- `jurisprudence_searches` - DATAJUD search results
- `distinguish_analyses` - Precedent comparison analyses
- `generated_documents` - AI-generated legal documents
- `notifications` - Email notifications

### `audit` Schema
- `logs` - Audit trail for all changes

## Best Practices

1. **Always test migrations** on a copy of production data before deploying
2. **Never edit** existing migration files after they've been applied
3. **Create backups** before running migrations in production
4. **Use transactions** (Alembic does this by default)
5. **Review auto-generated** migrations before applying

## Troubleshooting

### Migration stuck
```bash
# Check current state
alembic current

# Force stamp to a revision
alembic stamp head
```

### Conflicts
```bash
# Show heads
alembic heads

# Merge branches
alembic merge heads -m "merge branches"
```

### Reset everything (DANGER: Data loss!)
```bash
# Only in development!
alembic downgrade base
alembic upgrade head
```
