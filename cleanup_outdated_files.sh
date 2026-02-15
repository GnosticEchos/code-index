#!/bin/bash
# Cleanup script for outdated files in the code_index project
# Run this after the evaluation is complete

echo "Cleaning up outdated files..."

# Already removed during evaluation:
# - ARCHITECTURE_IMPROVEMENT_PLAN.md
# - BINARY_BUILD_README.md

# Root level outdated markdown files
echo "Removing outdated markdown files..."
rm -f CODE_REVIEW_REPORT.md

# Docs outdated markdown files
rm -f docs/final_summary.md
rm -f docs/indexing_status_tracking.md

# Tests outdated markdown files
rm -f tests/TEST_SUMMARY.md

# Backup files
rm -f src/code_index/parser.py.backup

# Large debug/temporary files
echo "Removing large debug files..."
rm -f nuitka-crash-report.xml   # 3.4MB
rm -f traceback                 # 9MB
rm -f treesitter_improvements_report.json
rm -f img_1770919707805.png

echo "Cleanup complete!"
echo ""
echo "Removed files:"
echo "  - CODE_REVIEW_REPORT.md (historical record of resolved issues)"
echo "  - docs/final_summary.md (completion summary, now outdated)"
echo "  - docs/indexing_status_tracking.md (design proposal document)"
echo "  - tests/TEST_SUMMARY.md (historical test summary)"
echo "  - src/code_index/parser.py.backup (old backup file)"
echo "  - nuitka-crash-report.xml (3.4MB debug file)"
echo "  - traceback (9MB debug file)"
echo "  - treesitter_improvements_report.json (temporary report)"
echo "  - img_1770919707805.png (temporary image)"
