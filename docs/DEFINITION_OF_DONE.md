# Definition of Done

A task is **not done** unless it meets all of these criteria:

## Core Requirements

1. **Works without the original author**
   - Code is documented and readable
   - No hardcoded paths or personal configurations
   - Clear error messages

2. **Produces the same output every time**
   - Deterministic results
   - No random elements (unless explicitly required)
   - Consistent formatting

3. **Reduces staff workload**
   - Automates manual processes
   - Eliminates repetitive tasks
   - Saves time compared to manual methods

4. **Fits cleanly into the existing system**
   - Follows folder structure conventions
   - Uses standard naming conventions
   - Integrates with existing tools

## Technical Requirements

### Code Quality
- [ ] Code follows Python style guidelines (PEP 8)
- [ ] Functions have docstrings
- [ ] Error handling is implemented
- [ ] No hardcoded values (use config)

### Testing
- [ ] Basic functionality tested
- [ ] Edge cases handled
- [ ] Error cases handled gracefully

### Documentation
- [ ] README updated if needed
- [ ] Usage examples provided
- [ ] Configuration documented

### Integration
- [ ] Works with existing schemas
- [ ] Uses shared metrics library
- [ ] Follows folder structure
- [ ] File naming conventions followed

## Report-Specific Requirements

### Trackman Reports
- [ ] CSV dropped → PDF appears automatically (if automated)
- [ ] Same layout every game
- [ ] No manual formatting required
- [ ] All required visuals present
- [ ] All required tables present
- [ ] Metadata correct (pitcher, game, date)

### Scouting Reports
- [ ] Updates game-to-game
- [ ] Structured hitter profiles
- [ ] Structured pitcher profiles
- [ ] Usage patterns included
- [ ] Internal notes integrated

### Dashboards
- [ ] Read-only (no data modification)
- [ ] Internal only (no public access)
- [ ] Uses metrics library
- [ ] Responsive and usable

## Checklist for Any Deliverable

Before marking a task as done, verify:

- [ ] Code runs without errors
- [ ] Output is consistent
- [ ] Documentation is clear
- [ ] Follows team standards
- [ ] Reduces manual work
- [ ] Can be maintained by others
- [ ] No single-person dependencies
- [ ] Confidentiality maintained

## Examples

### ✅ Done
- Trackman report generator that takes CSV + metadata → produces identical PDF every time
- Validation script that checks folder structure and reports errors clearly
- Metrics library with documented formulas and unit tests

### ❌ Not Done
- Script that only works on one person's computer
- Report that requires manual formatting after generation
- Tool that produces different outputs for the same input
- Code with no documentation or unclear error messages

