# Tape file for VHS recording of Yappy v0.2.0
# Output file
Output demo.gif

# Terminal setup
Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 800
Set Padding 20
Set WindowBar Colorful
Set Theme "Catppuccin Macchiato"

# 1. Show the About Screen
Type "yap --about"
Enter
Sleep 4s
Ctrl+L

# 2. Show the Schedule command
Type "yap schedule --list"
Enter
Sleep 2s
Ctrl+L

# 3. Launch Dashboard
Type "yap"
Enter
Sleep 5s

# 4. Navigate Dashboard (Show Strategy Panel)
# Assuming initial focus is the Dashboard
Sleep 2s

# 5. Open Config Editor (Show Tabs)
Type "c"
Sleep 3s

# 6. Switch to Advanced Tab
Type "right"
Sleep 3s

# 7. Interact with Persona Preset
Type "tab"
Sleep 1s
Type "down"
Sleep 1s
Type "enter"
Sleep 2s

# 8. Show Custom Prompt Area
Type "tab"
Sleep 2s

# 9. Exit Config
Type "escape"
Sleep 2s

# 10. Exit Yappy
Type "q"
Sleep 1s
