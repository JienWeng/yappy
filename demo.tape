# Tape file for VHS recording of Yappy
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

# Show About screen first
Type "yap --about"
Enter
Sleep 4s
Ctrl+L

# Start Yappy
Type "yap"
Enter
Sleep 4s

# Navigate to Stats Panel (assuming Tab or Arrow keys)
Tab
Sleep 2s
Tab
Sleep 2s

# Navigate to Config Editor
Tab
Sleep 2s

# Show the Config Editor's interactive fields
Down
Sleep 500ms
Down
Sleep 500ms
Down
Sleep 500ms

# Back to Live Feed
Tab
Sleep 3s

# Exit
Type "q"
Sleep 1s
