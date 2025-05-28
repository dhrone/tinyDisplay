# Legacy Documentation Backup

**Created:** December 2024  
**Reason:** BMAD methodology transition cleanup  

## Contents

This directory contains documentation files from the original tinyDisplay codebase that were created before the transition to the BMAD (Breakthrough Method of Agile Development) methodology.

### Moved Files

**Legacy System Documentation:**
- `transaction_usage.md` - Legacy transaction system guide
- `dynamicvalue_migration.md` - Legacy dynamic value migration
- `explicit_dependencies.md` - Legacy dependency system
- `global_dataset_safety.md` - Legacy dataset safety patterns
- `dependency_tracking.md` - Legacy dependency tracking
- `migration_guide.md` - Legacy d-prefix to dynamic() migration
- `coordinated_marquees.md` - Legacy marquee coordination system

**Legacy Directories:**
- `pageFiles/` - Legacy page configuration files
- `reference/` - Legacy API reference documentation
- `images/` - Legacy documentation images

## Why These Were Moved

These files document the legacy tinyDisplay architecture that is being replaced by the new reactive architecture (ring buffer + SQLite + asteval). The BMAD methodology has produced new documentation that reflects the current architectural direction:

- **New Architecture:** Ring buffer + SQLite + reactive patterns
- **New DSL:** DSL-first approach replacing JSON configurations
- **New Documentation:** Complete BMAD-generated docs in main `docs/` directory

## Preservation Purpose

These files are preserved for:
1. **Historical Reference:** Understanding the evolution of the project
2. **Migration Support:** Reference during legacy code migration
3. **Pattern Analysis:** Learning from previous architectural decisions
4. **Backup:** Safety net during transition period

## Current Documentation

For current project documentation, see the main `docs/` directory which contains:
- `index.md` - Main documentation hub
- Epic and story definitions
- New architecture guides
- Modern operational guidelines

---

**Note:** These files may be removed in a future cleanup after the migration to the new architecture is complete and validated. 