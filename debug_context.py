#!/usr/bin/env python3

# Debug script for context lines issue
code_chunk = "line 1\nline 2\nline 3\nline 4\nline 5"
lines = code_chunk.split('\n')
print(f"Lines: {lines}")
print(f"Length: {len(lines)}")

start_line = 3
end_line = 3
before = 1
after = 1

# Current calculation
start_idx = max(0, start_line - 1 - before)
end_idx = min(len(lines), end_line + after)

print(f"start_line: {start_line}")
print(f"end_line: {end_line}")
print(f"before: {before}, after: {after}")
print(f"start_idx: {start_idx}")
print(f"end_idx: {end_idx}")
print(f"Result: {lines[start_idx:end_idx]}")
print(f"Result length: {len(lines[start_idx:end_idx])}")

# Expected: lines 2, 3, 4 (1-based) = indices 1, 2, 3 (0-based)
expected_start = start_line - 1 - before  # 3 - 1 - 1 = 1
expected_end = end_line + after  # 3 + 1 = 4
print(f"Expected start_idx: {expected_start}")
print(f"Expected end_idx: {expected_end}")
print(f"Expected result: {lines[expected_start:expected_end]}")