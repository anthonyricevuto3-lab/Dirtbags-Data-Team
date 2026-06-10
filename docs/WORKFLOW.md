# Team Workflow Guide

## Daily Operations

### Post-Game Report Generation

1. **Trackman CSV arrives** (from Trackman export or staff)
2. **Drop file into watch directory** OR run manually:
   ```bash
   python scripts/generate_report.py <trackman.csv> --pitcher "Name" --opponent "UCLA" --game "Game1"
   ```
3. **Report appears automatically** (if using watcher) or manually in output directory
4. **Verify report** - Check that all sections are present and data looks correct

### Scouting Report Updates

1. **Gather data** from Trumedia, Sydex, internal notes
2. **Clean data** using schema validators if needed
3. **Generate/update report**:
   ```bash
   python scripts/generate_scouting_report.py --opponent "UCLA" --hitters hitters.csv --pitchers pitchers.csv
   ```
4. **Update game-to-game** as series progresses

## Weekly Tasks

- **Validate folder structure** - Run validation script on BaseballData/
- **Review metrics** - Ensure metrics library is producing expected results
- **Check logs** - Review error logs for issues
- **Update documentation** - Document any new processes or changes

## Monthly Tasks

- **Review definition of done** - Ensure all deliverables meet standards
- **Update dependencies** - Check for package updates
- **Backup data** - Ensure data is backed up appropriately
- **Team review** - Review workflow efficiency with team

## Communication

- **Ask questions immediately** - Don't let friction build up
- **Report issues promptly** - If something breaks, report it
- **Document changes** - When you modify processes, document them
- **Maintain confidentiality** - All data is internal only

## Quality Standards

Every deliverable must:
- Work without the original author
- Produce the same output every time
- Reduce staff workload
- Fit cleanly into existing system

See [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) for detailed checklist.

