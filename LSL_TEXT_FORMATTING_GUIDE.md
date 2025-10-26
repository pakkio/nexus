# LSL Text Formatting Guide for AI/LLM

## Using ~ for Line Breaks in llSetText Commands

When generating `llSetText` commands for Second Life/OpenSim integration, use `~` (tilde) as a placeholder for line breaks. The LSL script automatically converts `~` to `\n` for proper multi-line floating text display.

## Examples

### Single Line Text
```
llSetText=Mara - Village Herbalist
```
Displays: `Mara - Village Herbalist`

### Multi-Line Text with ~ 
```
llSetText=Mara~Village Herbalist~Ready to help
```
Displays:
```
Mara
Village Herbalist
Ready to help
```

### Quest Status Updates
```
llSetText=Quest Progress~Ancient Herbs: 2/5~Memory Elixir: In Progress
```
Displays:
```
Quest Progress
Ancient Herbs: 2/5
Memory Elixir: In Progress
```

### NPC Status Display
```
llSetText=Status Update~Currently: Brewing potions~Available for trade
```
Displays:
```
Status Update
Currently: Brewing potions
Available for trade
```

## Technical Details

1. **AI/LLM Side**: Use `~` in your llSetText commands
2. **Server Processing**: `~` characters are preserved in the command
3. **LSL Script**: Automatically converts `~` to `\n` before calling `llSetText()`
4. **SL Display**: Shows as proper multi-line floating text

## Best Practices

- Keep lines short (15-25 characters) for readability
- Use 2-3 lines maximum to avoid clutter
- Structure: Name~Role/Status~Action/Availability
- Example: `Lyra~Weaver of Memories~Seeking Memory Thread`

This system allows AI to create well-formatted, readable floating text that displays properly in Second Life and OpenSim environments.