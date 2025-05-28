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

## Additional Cleanup (December 2024)

### Legacy Source Code
- **`source-code/tinyDisplay/`** - Complete legacy source code directory
  - Contains old architecture with dataset.py, widget system, etc.
  - Replaced by new `src/tinydisplay/` structure in BMAD approach

### Legacy Tests
- **`tests/legacy-tests/`** - Complete legacy test suite
  - Tests for old architecture components
  - Replaced by new test structure per `docs/project-structure.md`

### Legacy Examples  
- **`examples/legacy-examples/`** - Legacy example applications
  - Examples using old architecture patterns
  - Replaced by new examples structure per BMAD guidelines

### Legacy Root Files
- **`root-files/`** - Miscellaneous legacy files from project root
  - `tinyDisplay-project-brief.md` - Duplicate project brief (now in `bmad-agent/data/`)
  - `marquee_class_dsl.md`, `application_widget_dsl.md` - Legacy DSL documentation
  - `DSL_implementation.md`, `PERFORMANCE_IMPROVEMENTS.md` - Legacy technical docs
  - `test_*.py` - Legacy test files that were in root
  - Various demo files, logs, and images

## Why These Were Moved

These files document and implement the legacy tinyDisplay architecture that is being replaced by the new reactive architecture (ring buffer + SQLite + asteval). The BMAD methodology has produced new documentation and will produce new implementation that reflects the current architectural direction:

- **New Architecture:** Ring buffer + SQLite + reactive patterns
- **New DSL:** DSL-first approach replacing JSON configurations  
- **New Documentation:** Complete BMAD-generated docs in main `docs/` directory
- **New Source Structure:** `src/tinydisplay/` following modern Python packaging
- **New Test Structure:** Organized test hierarchy per `docs/project-structure.md`

## Preservation Purpose

These files are preserved for:
1. **Historical Reference:** Understanding the evolution of the project
2. **Migration Support:** Reference during legacy code migration  
3. **Pattern Analysis:** Learning from previous architectural decisions
4. **Implementation Reference:** Understanding what worked in legacy system
5. **Backup:** Safety net during transition period

## Current Project Structure

For current project documentation and implementation, see:
- **Documentation:** `docs/` directory with BMAD-generated guides
- **Source Code:** `src/tinydisplay/` (to be created in Epic 1)
- **Tests:** `tests/` (to be created in Epic 1)  
- **Examples:** `examples/` (to be created in Epic 1)
- **BMAD Artifacts:** `bmad-agent/` directory

---

**Note:** These files may be removed in a future cleanup after the migration to the new architecture is complete and validated. 