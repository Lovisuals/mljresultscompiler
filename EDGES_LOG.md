# Edge Case Log - MLJ Results Compiler

## Identified Edge Cases

1. **State-Locked Commands**: The `/consolidate` command is only defined within the `SELECTING_FORMAT` state of the `ConversationHandler`. If a user sends the command outside this state (e.g., immediately after bot restart or if the state was lost), the command is ignored because it lacks a global handler.
   - *Impact*: User perceives the bot as broken/unresponsive ("does nothing").
   - *Fix*: Register `/consolidate` as both an entry point and a global command.

2. **Missing Conversational Modules**: `src.intent_engine` and `src.agent_router` are missing from the `src` directory, causing the entire conversational feature set to be disabled due to a shared `try...except` block.
   - *Impact*: Degraded user experience where the bot only responds with a static help message instead of detecting intent.
   - *Fix*: Decouple module imports or provide graceful degradation for missing components.

3. **Redundant Consolidation Flow**: The current flow requires multiple "Download Excel" clicks (one for preview, one for final delivery) which can be confusing and might lead users to think the process has stalled or restarted.
   - *Impact*: User confusion and potential perception of a "loop" that "does nothing" new.
   - *Fix*: Streamline the flow or clarify the steps in the UI.

4. **Case-Sensitive File Extensions**: The `filters.Document.FileExtension("xlsx")` might be case-sensitive depending on the environment/library version.
   - *Impact*: Users uploading `.XLSX` files might not trigger the document handler.
   - *Fix*: Use a case-insensitive check or include both versions in the filter.
