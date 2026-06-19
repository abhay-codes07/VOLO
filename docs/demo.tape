# Volo demo GIF — the README hero.
# 1. Install VHS once:  https://github.com/charmbracelet/vhs   (e.g. `winget install charmbracelet.vhs`
#    or `brew install vhs`; needs ffmpeg + ttyd).
# 2. From the repo root:  vhs docs/demo.tape   →  produces demo.gif
# 3. Move demo.gif to assets/ (or repo root) and add to README:  ![Volo demo](assets/demo.gif)

Output demo.gif

Set FontSize 18
Set Width 1180
Set Height 680
Set Theme "Dracula"
Set Padding 18
Set TypingSpeed 45ms

Hide
Type "clear" Enter
Show

Sleep 600ms
Type "uv run volo init examples.calc_agent:run --input '{""a"":2,""b"":3,""c"":4}'"
Sleep 700ms
Enter
Sleep 9s
