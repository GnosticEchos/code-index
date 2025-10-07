// ... existing code ...
@cli.command()
def search_info():
    """Show search result processing information."""
    try:
        # Initialize SearchResultProcessor
        result_processor = SearchResultProcessor(ctx.obj["error_handler")
        
        # Get search information
        validation_info = result_processor.get_validation_info()
        
        # Display information
        print("🔍 Search Result Processing Info")
        print("-" * 40)
        print("Validation rules:")
        print(f"  • Min query length: {validation_info.get('min_query_length', 2)}")
        print(f"  • Allowed characters: {validation_info.get('allowed_characters', 'letters, numbers, spaces, underscores, hyphens')}")
        print(f"  • Disallowed characters: {validation_info.get('disallowed_characters', 'special characters, symbols, punctuation')}")
        
        print("\n📋 Search Processing")
        print("-" * 40)
        print("Search processing information will be displayed here when available.")
        
        print("\n💡 Examples")
        print("-" * 40)
        print("  code-index search \"error handling\" --min-score 0.4 --workspace ./src --config code_index.json")
        print("  code-index search \"database connection\" --min-score 0.4 --workspace ./src --config code_index.json")
    except Exception as e:
        print(f"Error getting search info: {e}")
        sys.exit(1)